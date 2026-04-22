from __future__ import annotations

from typing import Literal

from config.settings import showAiErrorAlerts
from applybot.helpers import print_lg, critical_error_log, convert_to_json, smart_confirm
from applybot.ai.prompts import *


def _genai():
    """Lazy import: avoids `google.generativeai` deprecation FutureWarning on every process start."""
    import google.generativeai as genai

    return genai


def gemini_get_models_list():
    """
    Lists available Gemini models that support content generation.
    """
    try:
        genai = _genai()
        print_lg("Getting Gemini models list...")
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        print_lg("Available models:")
        for model in models:
            print_lg(f"- {model}")
        return models
    except Exception as e:
        critical_error_log("Error occurred while getting Gemini models list!", e)
        return ["error", e]

def gemini_create_client():
    """
    Configures the Gemini client and validates the selected model.
    * Returns a configured Gemini model object or None if an error occurs.
    """
    try:
        from config import secrets as sec

        genai = _genai()
        print_lg("Configuring Gemini client...")
        if not sec.llm_api_key or "YOUR_API_KEY" in sec.llm_api_key:
            raise ValueError("Gemini API key is not set. Please set it in `config/secrets.py`.")
        
        genai.configure(api_key=sec.llm_api_key)
        
        models = gemini_get_models_list()
        if "error" in models:
            raise ValueError(models[1])
        if not any(sec.llm_model in m for m in models):
             raise ValueError(f"Model `{sec.llm_model}` is not found or not available for content generation!")

        model = genai.GenerativeModel(sec.llm_model)
        
        print_lg("---- SUCCESSFULLY CONFIGURED GEMINI CLIENT! ----")
        print_lg(f"Using Model: {sec.llm_model}")
        print_lg("Check './config/secrets.py' for more details.\n")
        print_lg("---------------------------------------------")
        
        return model
    except Exception as e:
        error_message = f"Error occurred while configuring Gemini client. Make sure your API key and model name are correct."
        critical_error_log(error_message, e)
        if showAiErrorAlerts:
            if "Pause AI error alerts" == smart_confirm(f"{error_message}\n{str(e)}", "Gemini Connection Error", ["Pause AI error alerts", "Okay Continue"]):
                print_lg("AI error alerts paused by user.")
        return None

def gemini_completion(model, prompt: str, is_json: bool = False) -> dict | str:
    """
    Generates content using the Gemini model.
    * Takes in `model` - The Gemini model object.
    * Takes in `prompt` of type `str` - The prompt to send to the model.
    * Takes in `is_json` of type `bool` - Whether to expect a JSON response.
    * Returns the response as a string or a dictionary.
    """
    if not model:
        raise ValueError("Gemini client is not available!")

    try:
        # The Gemini API has a 'safety_settings' parameter to control content filtering.
        # For a job application helper, it's generally safe to set these to a less restrictive level
        # to avoid blocking legitimate content from resumes or job descriptions.
        # Less permissive than BLOCK_NONE: still allows typical résumé/job text while
        # retaining categorical guardrails against high-confidence harmful content.
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
        ]

        print_lg(f"Calling Gemini API for completion...")
        response = model.generate_content(prompt, safety_settings=safety_settings)
        
        # The response might be blocked. Check for that.
        if not response.parts:
            raise ValueError(
                "The response from the Gemini API was empty (possibly blocked by safety filters). "
                f"Prompt length was {len(prompt)} chars (not logged)."
            )

        result = response.text

        if is_json:
            # Clean the response to remove Markdown formatting
            if result.startswith("```json"):
                result = result[7:]
            if result.endswith("```"):
                result = result[:-3]
            
            return convert_to_json(result)
        
        return result
    except Exception as e:
        critical_error_log(f"Error occurred while getting Gemini completion!", e)
        return {"error": str(e)}

def gemini_extract_skills(model, job_description: str) -> list[str] | None:
    """
    Extracts skills from a job description using the Gemini model.
    * Takes in `model` - The Gemini model object.
    * Takes in `job_description` of type `str`.
    * Returns a `dict` object representing JSON response.
    """
    try:
        print_lg("Extracting skills from job description using Gemini...")
        prompt = extract_skills_prompt.format(job_description) + "\n\nImportant: Respond with only the JSON object, without any markdown formatting or other text."
        return gemini_completion(model, prompt, is_json=True)
    except Exception as e:
        critical_error_log("Error occurred while extracting skills with Gemini!", e)
        return {"error": str(e)}

def gemini_answer_question(
    model,
    question: str, options: list[str] | None = None, 
    question_type: Literal['text', 'textarea', 'single_select', 'multiple_select'] = 'text', 
    job_description: str = None, about_company: str = None, user_information_all: str = None,
    stream: bool = False
) -> str:
    """
    Answers a question using the Gemini API.
    """
    try:
        print_lg(f"Answering question using Gemini AI: {question}")
        user_info = user_information_all or ""
        prompt = ai_answer_prompt.format(user_info, question)

        if options and (question_type in ['single_select', 'multiple_select']):
            options_str = "OPTIONS:\n" + "\n".join([f"- {option}" for option in options])
            prompt += f"\n\n{options_str}"
            if question_type == 'single_select':
                prompt += "\n\nPlease select exactly ONE option from the list above."
            else:
                prompt += "\n\nYou may select MULTIPLE options from the list above if appropriate."
        
        if job_description:
            prompt += f"\n\nJOB DESCRIPTION:\n{job_description}"
        
        if about_company:
            prompt += f"\n\nABOUT COMPANY:\n{about_company}"

        return gemini_completion(model, prompt)
    except Exception as e:
        critical_error_log("Error occurred while answering question with Gemini!", e)
        return {"error": str(e)}
def gemini_check_job_relevance(
    model, 
    job_description: str, master_resume: str
) -> dict | ValueError:
    '''
    Function to check job relevance using Gemini.
    '''
    try:
        print_lg("-- CHECKING JOB RELEVANCE using Gemini AI")
        prompt = job_relevance_prompt.format(master_resume, job_description)
        return gemini_completion(model, prompt, is_json=True)
    except Exception as e:
        critical_error_log("Error occurred while checking job relevance with Gemini!", e)
        return {"error": str(e)}

def gemini_generate_resume(
    model, 
    job_description: str, master_resume: str
) -> dict | ValueError:
    '''
    Function to generate tailored resume content using Gemini.
    '''
    try:
        print_lg("-- TAILORING RESUME using Gemini AI")
        prompt = tailor_resume_prompt.format(master_resume, job_description)
        return gemini_completion(model, prompt, is_json=True)
    except Exception as e:
        critical_error_log("Error occurred while tailoring resume with Gemini!", e)
        return {"error": str(e)}

import os
import json

def generate_tailored_files(tailored_data, master_resume, output_dir, company_name, role_title):
    '''
    Generates .md and .tex tailored resumes.
    '''
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    base_filename = f"{company_name}_{role_title}".replace(" ", "_").replace("/", "_")
    md_path = os.path.join(output_dir, f"{base_filename}.md")
    tex_path = os.path.join(output_dir, f"{base_filename}.tex")

    # 1. Generate Markdown
    md_content = f"""# {master_resume['personal_info']['name']}
**Tailored for {company_name} - {role_title}**
{master_resume['personal_info']['location']} | {master_resume['personal_info']['email']} | {master_resume['personal_info']['linkedin']}

## Professional Summary
{tailored_data['tailored_summary']}

## Core Competencies
{chr(10).join(['- ' + s for s in tailored_data['core_competencies']])}

## Key Highlights
{chr(10).join(['- ' + h for h in tailored_data['tailored_highlights']])}

## Education
{chr(10).join([f"- **{e['degree']}**, {e['institution']} ({e['year']})" for e in master_resume['education']])}

## Patents
{chr(10).join(['- ' + p for p in master_resume['patents']])}
"""
    with open(md_path, 'w') as f:
        f.write(md_content)

    # 2. Generate LaTeX
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'base_resume.tex')
    try:
        with open(template_path, 'r') as f:
            tex_content = f.read()

        # Placeholders
        tex_content = tex_content.replace('[[NAME]]', master_resume['personal_info']['name'])
        tex_content = tex_content.replace('[[PHONE]]', master_resume['personal_info']['phone'])
        tex_content = tex_content.replace('[[EMAIL]]', master_resume['personal_info']['email'])
        tex_content = tex_content.replace('[[LINKEDIN]]', master_resume['personal_info']['linkedin'])
        tex_content = tex_content.replace('[[LINKEDIN_TEXT]]', master_resume['personal_info']['linkedin'].replace('https://', ''))
        tex_content = tex_content.replace('[[SUMMARY]]', tailored_data['tailored_summary'])

        # Skills
        skills_tex = "\\item \\textbf{Key Competencies:} " + ", ".join(tailored_data['core_competencies'])
        tex_content = tex_content.replace('[[SKILLS]]', skills_tex)

        # Highlights as Experience
        exp_tex = "\\textbf{Key Experience Highlights:}\n\\begin{itemize}[topsep=-0.1cm,itemsep=1pt]\n"
        for h in tailored_data['tailored_highlights']:
            exp_tex += f"    \\item {h}\n"
        exp_tex += "\\end{itemize}"
        tex_content = tex_content.replace('[[EXPERIENCE]]', exp_tex)

        # Education
        edu_tex = ""
        for e in master_resume['education']:
            edu_tex += f"    \\item \\textbf{{{e['degree']}}}, {e['institution']} \\hfill {e['year']}\n"
        tex_content = tex_content.replace('[[EDUCATION]]', edu_tex)

        # Patents
        pat_tex = ""
        for p in master_resume['patents']:
            pat_tex += f"    \\item {p}\n"
        tex_content = tex_content.replace('[[PATENTS]]', pat_tex)

        with open(tex_path, 'w') as f:
            f.write(tex_content)

    except Exception as e:
        print(f"Error generating LaTeX: {e}")

    return md_path, tex_path

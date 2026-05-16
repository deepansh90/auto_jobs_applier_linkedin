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

    p_info = master_resume.get('personal_info', {})
    
    # 1. Generate Markdown
    md_lines = [
        f"# {p_info.get('name', 'Applicant')}",
        f"**Tailored for {company_name} - {role_title}**",
        f"{p_info.get('location', '')} | {p_info.get('email', '')} | {p_info.get('linkedin', '')}",
        "",
        "## Professional Summary",
        tailored_data.get('tailored_summary', ''),
        "",
        "## Core Competencies",
        chr(10).join(['- ' + s for s in tailored_data.get('core_competencies', [])]),
        "",
        "## Key Highlights",
        chr(10).join(['- ' + h for h in tailored_data.get('tailored_highlights', [])])
    ]
    
    # Add optional Education
    edu = master_resume.get('education', [])
    if edu:
        md_lines.append("\n## Education")
        md_lines.append(chr(10).join([f"- **{e.get('degree', 'Degree')}**, {e.get('institution', 'Institution')} ({e.get('year', '')})" for e in edu]))

    # Add optional Patents
    patents = master_resume.get('patents', [])
    if patents:
        md_lines.append("\n## Patents")
        md_lines.append(chr(10).join(['- ' + p for p in patents]))

    with open(md_path, 'w', encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    # 2. Generate LaTeX
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'base_resume.tex')
    try:
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding="utf-8") as f:
                tex_content = f.read()

            # Placeholders
            tex_content = tex_content.replace('[[NAME]]', p_info.get('name', 'Applicant'))
            tex_content = tex_content.replace('[[PHONE]]', p_info.get('phone', ''))
            tex_content = tex_content.replace('[[EMAIL]]', p_info.get('email', ''))
            tex_content = tex_content.replace('[[LINKEDIN]]', p_info.get('linkedin', ''))
            tex_content = tex_content.replace('[[LINKEDIN_TEXT]]', p_info.get('linkedin', '').replace('https://', ''))
            tex_content = tex_content.replace('[[SUMMARY]]', tailored_data.get('tailored_summary', ''))

            # Skills
            skills_tex = "\\item \\textbf{Key Competencies:} " + ", ".join(tailored_data.get('core_competencies', []))
            tex_content = tex_content.replace('[[SKILLS]]', skills_tex)

            # Highlights as Experience
            exp_tex = "\\textbf{Key Experience Highlights:}\n\\begin{itemize}[topsep=-0.1cm,itemsep=1pt]\n"
            for h in tailored_data.get('tailored_highlights', []):
                exp_tex += f"    \\item {h}\n"
            exp_tex += "\\end{itemize}"
            tex_content = tex_content.replace('[[EXPERIENCE]]', exp_tex)

            # Education
            edu_tex = ""
            for e in edu:
                edu_tex += f"    \\item \\textbf{{{e.get('degree', 'Degree')}}}, {e.get('institution', 'Institution')} \\hfill {e.get('year', '')}\n"
            tex_content = tex_content.replace('[[EDUCATION]]', edu_tex)

            # Patents
            pat_tex = ""
            for p in patents:
                pat_tex += f"    \\item {p}\n"
            tex_content = tex_content.replace('[[PATENTS]]', pat_tex)

            with open(tex_path, 'w', encoding="utf-8") as f:
                f.write(tex_content)
        else:
            # Fallback if template missing
            pass

    except Exception as e:
        print(f"Error generating LaTeX: {e}")

    return md_path, tex_path

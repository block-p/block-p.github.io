"""Build the GitHub Pages site and both resumes from resume.json."""
import json
import re
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'dist'
ESCAPES = {
    '\\': r'\textbackslash{}',
    '~': r'\textasciitilde{}',
    '^': r'\textasciicircum{}',
    **{char: '\\' + char for char in '{}#$%&_'},
}


def tex(text):
    return ''.join(ESCAPES.get(char, char) for char in text)


def localized(text):
    # Double brackets mark left-to-right phrases inside Persian text.
    parts = re.split(r'\[\[([^\[\]]+)\]\]', text)
    return ''.join(r'\lr{' + tex(part) + '}' if i % 2 else tex(part)
                   for i, part in enumerate(parts))


def items(lines, persian):
    macro = r'\item ' if persian else r'\resumeItem'
    return '\n'.join(macro + '{' + localized(line) + '}' for line in lines)


def render_project(project, lang):
    title = localized(project['title'][lang])
    if project.get('url'):
        title = r'\href{' + tex(project['url']) + '}{' + title + '}'
    tech = tex(project['tech'])
    date = tex(project['date'][lang])
    bullets = items(project['bullets'][lang], lang == 'fa')
    if lang == 'fa':
        return '\n'.join([
            rf'\noindent\textbf{{{title}}} \hfill {date} \\',
            rf'\textit{{\small \lr{{{tech}}}}}',
            r'\begin{itemize}[leftmargin=*, label={$\bullet$}, nosep]',
            bullets,
            r'\end{itemize}',
        ])
    return '\n'.join([
        rf'\resumeProjectHeading{{\textbf{{{title}}} $|$ \footnotesize\emph{{{tech}}}}}{{{date}}}',
        r'\resumeItemListStart',
        bullets,
        r'\resumeItemListEnd',
    ])


def render(template, data, lang):
    course = data['course']
    values = {
        'NAME': tex(data['name'][lang]),
        'EMAIL': tex(data['email']),
        'EMAIL_URL': tex(data['email']),
        'GITHUB_URL': tex(data['github']),
        'GITHUB_LABEL': tex(data['github'].removeprefix('https://')),
        'PHONE': tex(data['phone_en']) + ' $|$' if data['phone_en'] else '',
        'SUMMARY': localized(data['summary'][lang]),
        'PROJECTS': '\n'.join(render_project(p, lang) for p in data['projects']),
        'PROVIDER': tex(course['provider']),
        'COURSE_BULLETS': items(course['bullets'][lang], lang == 'fa'),
    }
    for key, value in data['skills'].items():
        values['SKILLS_' + key.upper()] = tex(value)
    for group in ('course', 'education'):
        for key, value in data[group].items():
            if isinstance(value, dict) and isinstance(value.get(lang), str):
                values[f'{group}_{key}'.upper()] = localized(value[lang])
    return re.sub(r'@([A-Z_]+)@', lambda match: values[match[1]], template)


def main():
    data = json.loads((ROOT / 'resume.json').read_text(encoding='utf-8'))
    with TemporaryDirectory(prefix='portfolio-build-') as temporary:
        build = Path(temporary)
        for lang, name, compiler in (
            ('en', 'resume', 'pdflatex'),
            ('fa', 'resume-fa', 'xelatex'),
        ):
            source = build / f'{name}.tex'
            template = (ROOT / 'templates' / source.name).read_text(encoding='utf-8')
            source.write_text(render(template, data, lang), encoding='utf-8')
            subprocess.run(
                [compiler, '-no-shell-escape', '-interaction=nonstopmode',
                 '-halt-on-error', '-output-directory', str(build), str(source)],
                cwd=ROOT, check=True,
            )
        shutil.copytree(ROOT / 'site', OUTPUT, dirs_exist_ok=True)
        for filename in ('resume.pdf', 'resume-fa.pdf'):
            shutil.copyfile(build / filename, OUTPUT / filename)


if __name__ == '__main__':
    main()

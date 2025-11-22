import scrubadub

IGNORED_EXTENSIONS = {
    ".md", ".txt", ".rst", ".adoc",
    ".png", ".jpg", ".jpeg", ".svg", ".ico",
    ".lock", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".gitignore", ".dockerignore"
}

IGNORED_FILES = {
    "LICENSE", "Makefile", "Dockerfile", "requirements.txt"
}

def sanitize_diff(diff_text:str)->str:
    scrubber=scrubadub.Scrubber()
    clean_text=scrubber.clean(diff_text, replace_with="placeholder")
    return clean_text


def get_cleaned_files(arr:list[str])->list[str]:
    return [x for x in arr if x not in IGNORED_EXTENSIONS and IGNORED_FILES]





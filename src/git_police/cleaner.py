import scrubadub

def sanitize_diff(diff_text:str)->str:
    scrubber=scrubadub.Scrubber()
    clean_text=scrubber.clean(diff_text, replace_with="placeholder")
    return clean_text
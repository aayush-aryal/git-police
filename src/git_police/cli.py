import typer
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.live import Live
from rich.markdown import Markdown
import sys
from .llm import ask_interrogator, judge_answer
import os
from .helpers import get_cleaned_files

app=typer.Typer()
console=Console()

def git_diff():
    try:
        result=subprocess.run(["git", "diff" ,"--cached"], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError:
        return None

def get_diff_files():
    #idea: the most changed file is what you have been working on the most
    #get 
    try:
        result=subprocess.run(["git","diff","--cached","--name-only"], capture_output=True, text=True, check=True)
        files=result.stdout.splitlines()
        return files 
    except subprocess.CalledProcessError:
        return []

def get_sorted_diff_files(files:list[str])->list[str]:
    sorted_files=[]
    cmd=["git",'diff',"--cached","--numstat","--"]+files
    result=subprocess.run(cmd,text=True, capture_output=True)
    splitted=result.stdout.splitlines()
    for s in splitted:
        add,rm,fn=s.split("\t")
        sorted_files.append((add,rm,"".join(fn)))
    sorted_files=sorted(sorted_files, key=lambda x:int(x[0]),reverse=True)
    sorted_files=[x[2] for x in sorted_files]
    return sorted_files



def get_diff_string(files:list[str], max_count=12000)->str:
    curr_str=""
    for f in files:
        result=subprocess.run(["git","diff","--cached",f], capture_output=True, text=True,check=False)
        if len(curr_str)<=max_count:
            #not doing line by line cause it seems slow this will probably limit the max token and make it faster
            curr_str+=result.stdout
        else:
            curr_str+="[...OUTPUT TRUNCATED]"
            break
    return curr_str



@app.command()
def patrol(mode:str=typer.Option("local",help="local or global", envvar="GIT_POLICE_MODE"),
           model:str= typer.Option("phi4-mini:latest", help="The Ollama model to use (only for local mode)", envvar="GIT_POLICE_MODEL"),
           max_char:int=typer.Option(12000, help="Maximum characters sent to the model (if your local model is slow)", envvar="MAX_CHAR")):
    """Analyzes git diff, asks a question and decides whether to approve commit based on answer."""
    files=get_diff_files()
    relevant_files=get_cleaned_files(files)


    if not relevant_files:
        console.print("[dim]Only docs/config changed. Skipping interrogation.[/dim]")
        sys.exit(0)

    sorted_files=get_sorted_diff_files(relevant_files)

    if mode=="local":
        console.print(f"[dim](Speed depends on your hardware)[/dim]")
        diff=get_diff_string(sorted_files, max_char)
    else:
        diff = get_diff_string(sorted_files, 120000)
    if "[...OUTPUT TRUNCATED]" in diff:
        console.print("[bold yellow] Changes exceed max char, so asking question based on truncated string [/bold yellow]")
    if not diff or len(diff.strip()) == 0:
        console.print("[bold red] No staged changes found[/bold red]. Use[bold green] git add [/bold green]")
        sys.exit(0)
    
    console.print(Panel.fit(
        f"Git police: [bold yellow] {mode} [/bold yellow] mode [bold blue] analyzing... [/bold blue]",
        border_style="blue"
    ))

    console.print(f"\n[bold cyan underline]Question:[/bold cyan underline]")
    full_question=""
    with Live("", refresh_per_second=15, console= console) as live:
        for chunk in ask_interrogator(diff,mode,model):
            full_question+=chunk 
            live.update(Markdown(full_question))

    if not full_question or full_question.startswith("Error:"):
            console.print(f"\n [bold red] Error: {full_question}")
            sys.exit(1)
    

    answer=Prompt.ask("\n [bold cyan underline] Your answer [/]")

    with console.status("[bold yellow] Using our not so expert insights [/bold yellow]", spinner="dots"):
         verdict=judge_answer(diff, full_question, answer, mode, model)

         if verdict and "PASS" in verdict.strip().upper():
            console.print("\n[bold green]VERDICT: PASS[/bold green]")
            console.print("[dim]Commit allowed. Proceeding...[/dim]")
            sys.exit(0)
         else:
            console.print("\n[bold red] VERDICT: FAIL [/bold red]")
            console.print("Commit aborted")
            sys.exit(1)
        

def get_git_root():
    try:
        result=subprocess.run(
            ["git","rev-parse","show-toplevel"],
            capture_output=True, text=True, check=True
        ) 
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


    
@app.command()
def init():
    """Installs the pre-commit hook into the current Git repository."""
    #if we are not  in a Git repository
    git_root=get_git_root()

    if not git_root:
        console.print("[bold red]Error:[/bold red] Not a Git repository. Run 'git init' first.")
        sys.exit(1)   

    hook_dir=os.path.join(git_root,".git","hooks")
    hook_path=os.path.join(hook_dir,"pre-commit")    


    
    # shell script
    hook_content = (
        "#!/bin/sh\n"
        "exec < /dev/tty\n"
        "echo \"\n\n---RUNNING GIT POLICE INTERROGATION ---\"\n"
        # We call the 'patrol' function "$@ passes all the arguments passed dow"
        "git-police patrol \"$@\"\n" 
        "\n# Exit code of the patrol command determines if the commit proceeds.\n"
    )
    
    try:
        with open(hook_path, "w") as f:
            f.write(hook_content)
        
        # Make the file executable
        os.chmod(hook_path, 0o755)
        
        console.print("\n[bold green]✅Git Police Hook Installed![/bold green]")
        console.print(f"[dim]Run 'git commit' to test the interrogation. Default is local mode.[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]Error during installation:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    app()
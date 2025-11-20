import typer
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
import sys
from .llm import ask_interrogator, judge_answer
import os

app=typer.Typer()
console=Console()

def git_diff():
    try:
        result=subprocess.run(["git", "diff" ,"--cached"], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError:
        return None
    

@app.command()
def patrol(mode:str=typer.Option("local",help="local or global", envvar="GIT_POLICE_MODE"),
           model:str= typer.Option("gemma3:latest", help="The Ollama model to use (only for local mode)")):
    diff= git_diff()

    if not diff or len(diff.strip()) == 0:
        console.print("[bold red] No staged changes found. [/bold red]. use [bold green] git add [/bold green]")
        sys.exit(0)
    
    console.print(Panel.fit(
        f"Git police: [bold yellow] {mode} [/bold yellow] mode [bold blue] analyzing... [/bold blue]",
        border_style="blue"
    ))
    with console.status("[bold green] Generating question ... [/bold green]", spinner="dots"):
        question=ask_interrogator(diff, mode, model)
    
    if not question or question.startswith("Error:"):
            console.print(f"\n [bold red] Error: {question}")
            sys.exit(1)
    
    console.print(f"\n[bold red]INTERROGATION:[/bold red]")
    console.print(question)

    answer=Prompt.ask("\n Your answer")

    with console.status("[bold yellow] Using our not so expert insights [/bold yellow]", spinner="dots"):
         verdict=judge_answer(diff, question, answer, mode, model)

         if verdict and "PASS" in verdict.strip().upper():
            console.print("\n[bold green]VERDICT: PASS[/bold green]")
            console.print("[dim]Commit allowed. Proceeding...[/dim]")
            sys.exit(0)
         else:
            console.print("\n[bold red] VERDICT: FAIL [/bold red]")
            console.print("Commit aborted :(")
            sys.exit(1)
        
    


    
@app.command()
def init():
    """Installs the pre-commit hook into the current Git repository."""
    #if we are not  in a Git repository
    if not os.path.exists(".git"):
        console.print("[bold red]Error:[/bold red] Not a Git repository. Run this command inside your repo.")
        sys.exit(1)
        

    hook_path = ".git/hooks/pre-commit"
    
    # shell script
    hook_content = (
        "#!/bin/sh\n"
        "exec < /dev/tty\n"
        "echo \"\n\n---RUNNING GIT POLICE INTERROGATION ---\"\n"
        "# This command uses 'uv run' to execute your Python script\n"
        "# The arguments are passed to your patrol function.\n"
        # We call the 'patrol' function you just wrote
        "uv run git-police patrol \"$@\"\n" 
        "\n# Exit code of the patrol command determines if the commit proceeds.\n"
    )
    
    try:
        with open(hook_path, "w") as f:
            f.write(hook_content)
        
        # Make the file executable
        os.chmod(hook_path, 0o755)
        
        console.print("\n[bold green]✅ Git Police Hook Installed![/bold green]")
        console.print(f"[dim]Run 'git commit' to test the interrogation. Default is local mode.[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]Error during installation:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    app()
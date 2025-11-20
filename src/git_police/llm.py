import os 
from google import genai
from ollama import ChatResponse, chat
from .cleaner import sanitize_diff


def ask_interrogator(diff:str, mode:str, model:str):
    if mode=="local":
        response:ChatResponse= chat(model=model, messages=[
            {'role':'system', 'content':'You are a strict code reviewer.Ask one conceptual "WHY" question about the logic changes.'},
            {'role':'user','content':diff}

        ])
        return (response['message']['content'])
    elif mode=="global":
        cleaned_diff=sanitize_diff(diff)
        api_key=os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "Error: GEMINI_API_KEY not found in environment variables"
        
        try:
            client=genai.Client(api_key=api_key)

            gemini_response=client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"You are a Senior Code Reviewer. Ask one single, hard question about this code logic:\n\n{cleaned_diff}"
            )
            return gemini_response.text
        except Exception as e:
            return f"Error connecting to Gemini: {str(e)}"
    return "Error: Invalid mode selected"
            



def judge_answer(diff:str, question:str, answer:str, mode:str, model:str):
    evaluation_prompt= f"""
    You are a fair but helpful technical professor. Your task is to evaluate a student understanding of a code change

    Instructions
    1. Review the CODE DIFF, the QUESTION and the STUDENT'S ANSWER
    2. Determine if the answer is conceptually correct and fully addresses the question.
    3. Your entire response MUST be a single word: PASS or FAIL

    --CONTEXT -- 
    CODE DIFF: 
    {diff}

    QUESTION:
    {question}

    STUDENT ANSWER:
    {answer}

    --VERDICT--
    """
    if mode=="local":
        try:
            response=chat(model=model, messages=[
                {'role':'user','content':evaluation_prompt}

            ])
            return response['message']['content'].strip().upper()
        except Exception:
            return "ERROR: LOCAL JUDGE FAILED"
        
    elif mode=="global":
        try:
            client=genai.Client()
            response=client.models.generate_content(
                model="gemini-2.5-flash",
                contents=evaluation_prompt
            )
            return response.text
        except Exception:
            return "Error: GLOBAL JUDGE FAILED"

    return "ERROR: MODE FAILED"
        



    

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import tool
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

from agents.tools import (
    search_papers,
    filter_papers_hybrid,
    summarize_papers_with_groq,
    search_similar_projects,
    compute_similarity_scores,
    analyze_novelty,
    retrieve_from_knowledge_base
)

load_dotenv()

# -------------------- Tools --------------------
@tool
def search_literature(query: str) -> str:
    """Search academic papers, filter and return a concise summary."""
    papers = search_papers(query, max_results=20)
    if not papers:
        return "No papers found."
    relevant = filter_papers_hybrid(papers, query, embed_top_k=10, llm_top_n=5)
    summary = summarize_papers_with_groq(relevant)
    return summary

@tool
def check_similar_projects(idea: str) -> str:
    """Search GitHub/Hugging Face for similar projects, compute overlap, give novelty analysis."""
    projects = search_similar_projects(idea, max_results=10)
    if not projects:
        return "No similar projects found."
    scored = compute_similarity_scores(idea, projects)
    top = scored[:5]
    novelty = analyze_novelty(idea, top)
    return novelty + "\n\nTop matches:\n" + "\n".join(
        f"- [{p['source']}] {p['name']} (score: {s:.2f})" for s, p in top
    )

@tool
def ask_knowledge_base(question: str) -> str:
    """Answer using the user's own uploaded PDFs (personal knowledge base)."""
    return retrieve_from_knowledge_base(question)

# -------------------- Orchestrator --------------------
llm = ChatGroq(
    model="llama-3.1-8b-instant",   # or "mixtral-8x7b-32768" – choose whatever you have access to
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)

tools = [search_literature, check_similar_projects, ask_knowledge_base]

# Simple system prompt – the agent will decide which tools to call
system_prompt = (
    "You are an AI research and project assistant. Help the user plan their technical project. "
    "Use the available tools to search literature, check for similar projects, and answer questions "
    "from their knowledge base. Be conversational and proactive."
)

agent = create_tool_calling_agent(llm, tools, system_prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
from fastmcp import FastMCP
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# 1. Create the MCP Server
mcp = FastMCP("Academic Research Server")

# 2. Define the Tool
@mcp.tool()
def search_arxiv(query: str, max_results: int = 5) -> str:
    """
    Searches arXiv.org for academic papers. 
    Returns Title, Authors, Published Date, Link, and Summary.
    """
    print(f"Searching ArXiv for: {query}") 
    
    base_url = 'http://export.arxiv.org/api/query?'
    # URL Encode the query to handle spaces safely
    safe_query = urllib.parse.quote(query)
    
    search_params = f'search_query=all:{safe_query}&start=0&max_results={max_results}'
    final_url = base_url + search_params
    
    try:
        with urllib.request.urlopen(final_url) as url:
            data = url.read().decode('utf-8')
            
        root = ET.fromstring(data)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        
        results = []
        for entry in root.findall('atom:entry', namespace):
            # Extract basic info
            title = entry.find('atom:title', namespace).text.strip().replace('\n', ' ')
            link = entry.find('atom:id', namespace).text.strip()
            published = entry.find('atom:published', namespace).text.strip()[:10]
            
            # Extract Authors (The Critical Fix)
            author_list = []
            for author in entry.findall('atom:author', namespace):
                name = author.find('atom:name', namespace).text.strip()
                author_list.append(name)
            authors_str = ", ".join(author_list)

            # Extract Summary and clean it up
            summary_raw = entry.find('atom:summary', namespace).text
            summary = summary_raw.strip().replace('\n', ' ') if summary_raw else "No summary."
            
            # Format the output clearly for the LLM
            results.append(
                f"Title: {title}\n"
                f"Authors: {authors_str}\n"
                f"Date: {published}\n"
                f"Link: {link}\n"
                f"Summary: {summary}\n"
                f"---"
            )
            
        if not results:
            return "No papers found."
            
        return "\n".join(results)

    except Exception as e:
        return f"Error searching ArXiv: {str(e)}"

if __name__ == "__main__":
    mcp.run()
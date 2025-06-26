from ii_agent.tools.base import ToolImplOutput


def format_screenshot_tool_output(screenshot: str, msg: str, log: str = None, network: str = None) -> ToolImplOutput:
    tool_output = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": screenshot,
            },
        },
        {"type": "text", "text": msg},
    ]
    
    if log:
        tool_output.append({
            "type": "text",
            "text": log
        })
        
    if network:
        tool_output.append({
            "type": "text",
            "text": network
        })
        
    return ToolImplOutput(
        tool_output=tool_output,
        tool_result_message=msg,
    )
    
def get_console_logs(browser, param):
    logs = None
    if param:
        captured = browser.captured_logs
        url = browser.current_page.url
        # Handle cases that have / at the end
        if url[-1] == '/':
            url = url[:-1]
        logs = '\n\n'.join(captured.get(url, []))
        browser.captured_logs[url] = [] # Reset the log
    return logs

def get_network_responses(browser, param):
    responses = None
    if param:
        logged = browser.network_logs
        url = browser.current_page.url
        if url[-1] == '/':
            url = url[:-1]
        responses = '\n\n'.join(logged.get(url, []))
        browser.network_logs[url] = [] # Reset the log 
    return responses
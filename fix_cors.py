import re

def fix_cors():
    # Read the content of main.py
    with open("app/main.py", "r") as file:
        content = file.read()
    
    # Define the new CORS configuration
    cors_config = """# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)"""

    # Use regex to replace the CORS configuration
    pattern = r"# Set up CORS middleware.*?\)"
    updated_content = re.sub(pattern, cors_config, content, flags=re.DOTALL)
    
    # Write back to main.py
    with open("app/main.py", "w") as file:
        file.write(updated_content)
    
    print("CORS configuration updated successfully.")

if __name__ == "__main__":
    fix_cors() 
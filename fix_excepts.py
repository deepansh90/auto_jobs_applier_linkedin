import re
import sys

def main():
    file_path = "applybot/__main__.py"
    with open(file_path, "r") as f:
        content = f.read()
    
    # Replace bare except: pass
    content = re.sub(r'(\s+)except:\s*pass', r'\1except Exception as e:\n\1    print_lg(f"[ERROR] Ignored Exception: {e}")\n\1    pass', content)
    
    # Replace bare except:
    # Need to be careful with negative lookahead so we don't match "except Exception:"
    content = re.sub(r'(\s+)except:(?! \w)(?!\s*pass)', r'\1except Exception as e:\n\1    print_lg(f"[ERROR] Caught Exception: {e}")', content)
    
    with open(file_path, "w") as f:
        f.write(content)

if __name__ == "__main__":
    main()

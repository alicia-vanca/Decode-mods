import os
import re
import shutil
import subprocess
import json

# Global dictionary to cache string.char conversions
char_sequence_cache = {}

# File to store the cache
CACHE_FILE = "string_char_cache.json"

def save_char_sequence_cache():
    if not char_sequence_cache:
        print("Cache is empty, nothing to save")
        return
        
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(char_sequence_cache, f, ensure_ascii=False, indent=4)
        print(f"Saved {len(char_sequence_cache)} sequences to cache")
    except Exception as e:
        print(f"Error saving cache: {e}")

def load_char_sequence_cache():
    global char_sequence_cache
    try:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    char_sequence_cache = json.load(f)
                print(f"Loaded {len(char_sequence_cache)} cached sequences")
            except json.JSONDecodeError:
                print("Cache file is corrupted, starting with empty cache")
                char_sequence_cache = {}
        else:
            char_sequence_cache = {}
            print("No cache file found, starting with empty cache")
    except Exception as e:
        print(f"Error loading cache: {e}")
        char_sequence_cache = {}

# Initialize cache at startup
load_char_sequence_cache()

def format_lua_content(content, file_path):
    print(f"Start format output file")
    try:
        stylua_path = r"C:\Users\Kuriyama Mirai\.cargo\bin\stylua.exe"
        
        if not os.path.exists(stylua_path):
            print(f"Warning: stylua not found at {stylua_path}")
            return content
            
        # Create a temporary file for the content
        temp_file = file_path + ".temp"
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(content)
            
        try:
            result = subprocess.run([stylua_path, temp_file], check=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"StyLua failed for {file_path}: {result.stderr}")
                return content
                
            # Read the formatted content
            with open(temp_file, "r", encoding="utf-8") as f:
                formatted_content = f.read()
                
            print(f"Format done")
            return formatted_content
            
        except subprocess.TimeoutExpired:
            print(f"StyLua timed out for {file_path}")
            return content
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
    except Exception as e:
        print(f"Formatting failed: {e}")
        return content

    
def do_math(match):
    print(match.group(0))
    # Turn "3 + (2 * 5) - 6 / (1 + 1)" into "10"
    return str(eval(match.group(0)))
    
def merge_matchs(match):
    # match: "u".."t".."i".."l".."s"    
    pattern = r'"([^"]*)"' 
    
    # splited_strings: {'u', 't', 'i', 'l', 's'}
    splited_strings = re.findall(pattern, match.group(0))
    
    # utils -> "utils"
    return '"' + ''.join(splited_strings) + '"'

def merge_splited_strings(input_string):    
    # Merge splited strings
    # input: "b".."e".."h".."a".."v".."i".."o".."u".."r".."s"
    # output: "behaviours"
    pattern = r'(?<!\\)("(?:\\"|\\\\|[^"\n])*"(?:\s*(?:\.\.)[ \t]*"(?:\\"|\\\\|[^"\n])*")+)'
    return re.sub(pattern, merge_matchs, input_string)
    
def ascii_to_char(num):
    char = chr(num)
    if char in ['"', '\\', "'", "\n"]:
        char = '\\' + char
    return char
    
def convert_ascii_in_text(content):
    # Regular expression to find ASCII sequences
    ascii_pattern = re.compile(r'(?<!\\)\\(\d{1,3})')

    def match_ascii_to_char(match):
        # Convert ASCII code to character
        num = int(match.group(1))
        if num >= 32 and num <= 126:
            return ascii_to_char(num)
        else:
            return match.group(0)

    # Replace all ASCII sequences with their corresponding characters
    converted_content = ascii_pattern.sub(match_ascii_to_char, content)
    return converted_content
    
    
def convert_hex_to_decimal_and_ascii_to_char(text):
    # Pattern matches 0x followed by hex digits
    pattern = r'0x[0-9a-fA-F]+'
    
    # Keep track of states
    result = ''
    quote_stack = []
    in_comment = False
    in_multiline_comment = False
    last_pos = 0
    
    # Find all quotes, comments, and hex numbers
    for match in re.finditer(r'(?<!\\)(?:\\\\)*[\'"]|--\[\[|\]\]|\n|(' + pattern + ')|--', text):
        matched_text = match.group(0)
        
        # Handle different types of matches
        
        if "'" in matched_text or '"' in matched_text :
            matched_text = matched_text[-1]
            
        if not (in_comment or in_multiline_comment) and matched_text in ['"', "'"]:
            if not quote_stack:
                # Start new quote
                quote_stack.append(matched_text)
                result += text[last_pos:match.end()]
                last_pos = match.end()
            elif quote_stack[0] == matched_text:
                # End matching quote
                quote_stack.pop()
                # Find all ASCII sequences in quotes and convert them to corresponding characters
                result += convert_ascii_in_text(text[last_pos:match.end()])
                last_pos = match.end()
        elif not quote_stack:
            if in_multiline_comment:
                if matched_text == ']]':
                    in_multiline_comment = False
                result += text[last_pos:match.end()]
            elif matched_text == "\n" and in_comment:
                # Reset single-line comment at newline
                in_comment = False
                result += text[last_pos:match.end()]
            elif in_comment:
                result += text[last_pos:match.end()]
            elif matched_text == '--[[':
                in_multiline_comment = True
                result += text[last_pos:match.end()]
            elif matched_text == '--':
                in_comment = True
                result += text[last_pos:match.end()]
            elif not in_comment and match.group(1):
                # Convert hex to decimal when not in quotes or comments
                hex_num = match.group(1)
                decimal_num = str(int(hex_num, 16))
                result += text[last_pos:match.start()] + decimal_num
            else:
                result += text[last_pos:match.end()]
                
            last_pos = match.end()
    
    # Add remaining text
    result += text[last_pos:]
    return result
    
def process_char_sequence(sequence):
    try:
        # Process all numbers in one go
        nums = []
        for c in sequence.split(','):
            c = c.strip()
            if not c:
                continue
                
            # Handle expressions first
            if any(op in c for op in '+-*/'):
                # Convert hex to decimal first
                c = re.sub(r'0x([0-9a-fA-F]+)', lambda m: str(int(m.group(1), 16)), c)
                num = eval(c, {"__builtins__": {}}, {})
                nums.append(num)
            # Then handle hex
            elif c.startswith('0x'):
                nums.append(int(c, 16))
            # Then handle decimal
            elif c.isdigit():
                nums.append(int(c))
            else:
                nums.append(int(c, 0))
        
        # Store both the original sequence and the evaluated numbers
        result = ''
        for num in nums:
            print(num)
            if num < 32 or num > 126:  # Non-printable ASCII characters
                char = f'\"\\{num}\"'
            else:
                char = f'\"{ascii_to_char(num)}\"'

            if result == '':
                    result += char
            else:
                result += f'..{char}'
                
        result = merge_splited_strings(result)
        return {
            'original': sequence,
            'numbers': nums,
            'result': result
        }
    except Exception as e:
        print(f"Error processing sequence: {sequence} - {str(e)}")
        return None
        
def find_variables_of_string_char(input_string, existing_vars=None):
    # Pattern to match variable assignment but not commented lines
    pattern = r'^\s*(?!.*--.*?)(?:local\s+)?(\w+)\s*=\s*string\s*\[\s*["\']char["\']?\s*\]'
    
    # Find all matches
    matches = re.finditer(pattern, input_string, re.MULTILINE)
    
    # Go through matches until we find one that's not in existing_vars
    for match in matches:
        var_name = match.group(1)
        if not existing_vars or var_name not in existing_vars:
            return var_name
            
    direct_call_string_char = 'string["char"]'
    if input_string.find(direct_call_string_char+'(') != -1 and direct_call_string_char not in existing_vars:
        return direct_call_string_char
        
    return None
    
    
def decrypt_string_char(input_string):
    result = ""
    last_pos = 0
    cache_modified = False
    string_char_var = "string.char("
    string_char_var_list = []
    
    while True:
        # Find next occurrence of 'string.char('
        start = input_string.find(string_char_var, last_pos)
        if start == -1:  # No more string.char sequences found
            result += input_string[last_pos:]
            string_char_var = find_variables_of_string_char(result, string_char_var_list)
            if string_char_var:
                string_char_var_list.append(string_char_var)
                string_char_var += '('
                last_pos = 0
                start = result.find(string_char_var, last_pos)
            if start == -1:
                break
            else:
                input_string = result
                result = ""                
            
        # Add everything from last position to current string.char
        result += input_string[last_pos:start]
        
        # Find matching closing bracket
        i = start + len(string_char_var)  # Skip 'string.char('
        bracket_count = 1
        
        while i < len(input_string) and bracket_count > 0:
            if input_string[i] == '(':
                bracket_count += 1
            elif input_string[i] == ')':
                bracket_count -= 1
            i += 1
            
        if bracket_count == 0:
            # Extract content inside brackets
            content = input_string[start+len(string_char_var):i-1]
            print(f'content: {input_string[start:i]}')
            
            replacement = None
            
            # Check if we've processed this sequence before
            if content in char_sequence_cache and False:
                replacement = char_sequence_cache[content]["result"]
                print(f'cached replacement: {replacement}\n')
            else:
                # Process new sequence and cache it
                processed = process_char_sequence(content)
                if processed:
                    char_sequence_cache[content] = processed
                    replacement = processed["result"]
                    cache_modified = True
                    print(f'new replacement: {replacement}\n')
            
            if replacement:
                if input_string[i] == ':':
                    result += "(" + replacement + ")"
                else:
                    result += replacement
            else:
                # If processing failed, keep original
                result += input_string[start:i]
                
            last_pos = i
        else:
            # If no matching bracket found, keep original and continue
            result += input_string[start:start+len(string_char_var)]
            last_pos = start + len(string_char_var)
            
    # Save cache if new entries were added
    #if cache_modified:
        #save_char_sequence_cache()
        
    return result

def hex_to_oct(match):
    # Convert the hexadecimal value to decimal
    decimal_value = int(match.group(0)[2:], 16)
    # Convert the decimal value to octal
    octal_value = oct(decimal_value)[2:]
    # Return the octal escape sequence
    return f"\\{octal_value}"

def replace_reversed_strings(content):
    # Define the pattern to match any string in the format "<string>":reverse() or ("<string>"):reverse()
    pattern = r'(?:"([^"]+)":reverse\(\)|\("([^"]+)"\):reverse\(\))'

    # Function to replace the matched pattern with the original string
    def replace_match(match):
        # Get the original string from the match groups
        original_string = match.group(1) or match.group(2)
        
        # Reverse the original string to get the correct replacement
        reversed_string = re.sub(r'\\x[0-9a-fA-F]{2}', hex_to_oct, repr((original_string.encode().decode('unicode_escape'))[::-1])[1:-1])
        return f'"{reversed_string}"'

    # Replace the matched patterns with the original string
    updated_content = re.sub(pattern, replace_match, content)

    return updated_content

def decrypt_lua(input_string):
        
    # Find all hexadecimal numbers and convert them to decimal
    # Find all ascii in quotes and convert them to corresponding characters
    transformed_string = convert_hex_to_decimal_and_ascii_to_char(input_string)
    
    # Decode string.char
    decoded_string = decrypt_string_char(transformed_string)

    reversed_strings = replace_reversed_strings(decoded_string)
        
    # Merge splited strings
    merged_decrypt_string = merge_splited_strings(reversed_strings)

    # Calculate all the simple math
    # "2024-09-16" caused error: leading zeros in decimal integer literals are not permitted; use an 0o prefix for octal integers
    # expression_pattern = r'(?:[(]\s*)*\d+[)]*(?:\s*[-+*/]\s*(?:[(]*\s*\d+(?:\s*[)])*))+'
    # calculated_string = re.sub(expression_pattern, do_math, transformed_string)
    
    return merged_decrypt_string

def decrypt_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    content = decrypt_lua(content)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(format_lua_content(content, file_path))
    print(f"Successfully decrypted file: {file_path}")


def decrypt_folder(folder_path):
    new_folder_path = folder_path + "_decrypted"

    # Check if the duplicate folder exists
    if os.path.exists(new_folder_path):
        user_input = (
            input(
                f"\nThe folder '{new_folder_path}' already exists.\nDo you want to delete it and create a new one? (yes/no): "
            )
            .strip()
            .lower()
        )
        if user_input in ["yes", "y"]:
            try:
                shutil.rmtree(new_folder_path)
                print(f"\nDeleted existing folder: \n{new_folder_path}")
            except Exception as e:
                print(f"\nError deleting folder: {e}")
                raise SystemExit
        elif user_input in ["no", "n"]:
            print("Operation cancelled by user.")
            raise SystemExit
        else:
            print("Invalid input. Operation cancelled.")
            raise SystemExit

    # Duplicate the folder
    try:
        shutil.copytree(folder_path, new_folder_path)
        print(f"\nDuplicated folder to: \n{new_folder_path}")
    except Exception as e:
        print(f"\nError duplicating folder: {e}")
        raise SystemExit

    total_files = 0
    lua_files = []
    for root, _, files in os.walk(new_folder_path):
        for file in files:
            if file.endswith(".lua"):
                total_files += 1
                lua_files.append(os.path.join(root, file))

    print(f"\nFound {total_files} .lua files to process")
	
    # Process files with progress tracking
    processed_files = 0
    for file_path in lua_files:
        processed_files += 1
        print(f"\nProgress: {processed_files}/{total_files} files")

        print(f"Decrypting file: {file_path}")
        decrypt_file(file_path)


def require_valid_folder_directory():
    while True:
        folder_path = input("\nPlease enter the path of your folder: ")

        if os.path.isdir(folder_path):
            print(f"\nValid directory: {folder_path}")
            break
        else:
            print(
                f"\nError: '{folder_path}' is not a valid directory. Please try again."
            )

    return folder_path.rstrip('\\')


if __name__ == "__main__":
    folder_path = require_valid_folder_directory()
    print(f"Starting decryption for folder: {folder_path}")
    decrypt_folder(folder_path)
    print("\nDecryption completed.")


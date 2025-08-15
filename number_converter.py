import logging
from flask import Flask, render_template_string, request

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
MAX_INPUT_LENGTH = 100
MAX_PRECISION = 16

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Universal Number Converter - Fractional Support</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');
        body { font-family: 'Roboto', sans-serif; margin: 0; padding: 0;
            background: linear-gradient(135deg, #667eea, #764ba2); min-height: 100vh;
            color: #f1f1f1; display: flex; justify-content: center; align-items: center; }
        .container { background: rgba(0,0,0,0.75); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.3);
            width: 700px; padding: 30px 40px 40px 40px; box-sizing: border-box; }
        h1 { margin-bottom: 10px; font-weight: 700; font-size: 2.4rem; letter-spacing: 1.2px; text-align: center; text-shadow: 2px 2px 6px #222; }
        label { display: block; margin-top: 20px; font-weight: 600; user-select: none; letter-spacing: 0.05em; }
        input[type=text], select, button {
            margin-top: 8px; padding: 12px 15px; font-size: 1rem; border-radius: 8px; border: none;
            width: 100%; outline: none; box-sizing: border-box; transition: 0.3s; font-family: monospace;
        }
        input[type=text]:focus, select:focus { box-shadow: 0 0 8px #764ba2; background-color: #fff; color: #333; }
        button { background: #764ba2; color: #fff; cursor: pointer; font-weight: 700; letter-spacing: 0.1em;
            margin-top: 28px; transition: background-color 0.3s ease; }
        button:hover { background: #667eea; }
        .result, .error {
            margin-top: 25px; padding: 15px; border-radius: 8px; box-sizing: border-box;
            font-family: 'Courier New', Courier, monospace; white-space: pre-wrap; word-wrap: break-word;
            font-size: 1rem;
        }
        .result { background: #222; color: #a8ffc7; line-height: 1.35; box-shadow: inset 0 0 10px #2ecc71; }
        .error { background: #ff4c4c; color: #fff; font-weight: bold; box-shadow: inset 0 0 10px #ff0000; }
        .op-select { margin-top: 15px; display: flex; gap: 12px; font-weight: 700; user-select: none; }
        .op-select label { cursor: pointer; }
        footer { user-select: none; font-size: 0.9rem; text-align: center; color: #ccc; margin-top: 30px; }
        @media(max-width: 780px) {
            .container { width: 95vw; padding: 25px 20px; }
            input[type=text], select, button { font-size: 0.9rem; }
            h1 { font-size: 1.8rem; }
        }
    </style>
</head>
<body>
<div class="container">
    <h1>Universal Number Converter</h1>
    <form method="post" novalidate>
        <label for="number">Enter Number:</label>
        <input type="text" name="number" id="number" value="{{ number|default('') }}" required placeholder="Enter your number (float or integer)" />
        <label for="base_in">Base of Input Number:</label>
        <select name="base_in" id="base_in" required>
            {% for bval, bname in bases %}
                <option value="{{ bval }}" {% if bval == base_in %}selected{% endif %}>{{ bname }} (base {{ bval }})</option>
            {% endfor %}
        </select>
        <div class="op-select">
            <label><input type="radio" name="operation" value="convert" {% if operation == 'convert' or not operation %}checked{% endif %} /> Convert</label>
            <label><input type="radio" name="operation" value="add" {% if operation == 'add' %}checked{% endif %} /> Add</label>
            <label><input type="radio" name="operation" value="subtract" {% if operation == 'subtract' %}checked{% endif %} /> Subtract</label>
        </div>
        <div id="secondNumberDiv" style="margin-top: 20px; {% if operation == 'add' or operation == 'subtract' %}display:block;{% else %}display:none;{% endif %}">
            <label for="number2">Second Number (for add/subtract):</label>
            <input type="text" name="number2" id="number2" value="{{ number2|default('') }}" placeholder="Enter second number (same base)" />
        </div>
        <button type="submit">Calculate</button>
    </form>
    {% if error %}
        <div class="error">{{ error }}</div>
    {% endif %}
    {% if results %}
        <h2>Results:</h2>
        <div class="result">
            <strong>Decimal:</strong> {{ results.decimal }}<br>
            <strong>Binary:</strong> {{ results.binary }}<br>
            <strong>Octal:</strong> {{ results.octal }}<br>
            <strong>Hexadecimal:</strong> {{ results.hex }}<br><br>
            {% if results.get("bcd") is not none %}
            <strong>BCD (Binary Coded Decimal):</strong> {{ results.bcd }}<br>
            <strong>Gray Code:</strong> {{ results.gray }}<br>
            <strong>Excess-3 Code:</strong> {{ results.excess3 }}<br><br>
            {% endif %}
            {% if results.get("ones_complement") is not none %}
            <strong>One's Complement (8-bit padded):</strong> {{ results.ones_complement }}<br>
            <strong>Two's Complement (8-bit padded):</strong> {{ results.twos_complement }}<br>
            {% endif %}
        </div>
    {% endif %}
</div>
<script>
    document.addEventListener('DOMContentLoaded', function() {
        const opButtons = document.querySelectorAll('input[name="operation"]');
        const secondNumberDiv = document.getElementById('secondNumberDiv');
        function updateSecondNumberVisibility() {
            let selected = document.querySelector('input[name="operation"]:checked').value;
            if (selected == 'add' || selected == 'subtract') {
                secondNumberDiv.style.display = 'block';
                document.getElementById('number2').required = true;
            } else {
                secondNumberDiv.style.display = 'none';
                document.getElementById('number2').required = false;
            }
        }
        opButtons.forEach(radio => radio.addEventListener('change', updateSecondNumberVisibility));
        updateSecondNumberVisibility(); // Run on page load
    });
</script>
<footer>
    &copy; 2025 Universal Number Converter
</footer>
</body>
</html>
"""

def ones_complement(bin_str):
    return ''.join('1' if b == '0' else '0' for b in bin_str)

def twos_complement(bin_str):
    ones = ones_complement(bin_str)
    return bin(int(ones, 2) + 1)[2:].zfill(len(bin_str))

def decimal_to_bcd(n_str):
    return ' '.join(f"{int(d):04b}" for d in n_str if d.isdigit())

def decimal_to_gray(n):
    return bin(n ^ (n >> 1))[2:]

def decimal_to_excess_3(n_str):
    return ' '.join(f"{(int(d) + 3):04b}" for d in n_str if d.isdigit())

def validate_and_parse(num_str: str, base: int):
    if not num_str or not num_str.strip():
        return None, "Input cannot be empty."
    cleaned_str = num_str.strip().upper()
    if len(cleaned_str) > MAX_INPUT_LENGTH:
        return None, f"Input is too long (max {MAX_INPUT_LENGTH} characters)."
    sign = 1
    if cleaned_str.startswith(('-', '+')):
        if cleaned_str[0] == '-':
            sign = -1
        cleaned_str = cleaned_str[1:]
    valid_chars = {
        2: '01',
        8: '01234567',
        10: '0123456789.',
        16: '0123456789ABCDEF'
    }
    allowed_chars = valid_chars.get(base)
    if not allowed_chars:
        return None, "Internal error: Unsupported base."
    for char in cleaned_str:
        if char not in allowed_chars:
            return None, f"Invalid character '{char}' for base {base}."
    if '.' in cleaned_str:
        if base != 10:
            return None, f"Fractional input is only supported for base 10."
        if cleaned_str.count('.') > 1:
            return None, "Invalid number: multiple decimal points found."
    try:
        if base == 10:
            value = float(cleaned_str)
        else:
            value = int(cleaned_str, base)
        return sign * value, None
    except ValueError:
        return None, f"Could not parse '{num_str}' as a valid base {base} number."
    except Exception as e:
        logging.error(f"Unexpected parsing error: {e}")
        return None, "An unexpected error occurred during parsing."

def format_from_decimal(dec_num: float, to_base: int):
    if to_base not in [2, 8, 10, 16]:
        raise ValueError("Target base must be 2, 8, 10, or 16.")
    if dec_num == 0:
        return "0"
    sign = "-" if dec_num < 0 else ""
    dec_num = abs(dec_num)
    integer_part = int(dec_num)
    fractional_part = dec_num - integer_part
    if to_base == 10:
        int_str = str(integer_part)
    elif to_base == 16:
        int_str = hex(integer_part)[2:].upper()
    elif to_base == 8:
        int_str = oct(integer_part)[2:]
    else:
        int_str = bin(integer_part)[2:]
    if fractional_part < 1e-9:
        return sign + int_str
    frac_str = ""
    if to_base == 10:
        frac_str = format(fractional_part, f'.{MAX_PRECISION}f').rstrip('0')[1:]
    else:
        hex_digits = "0123456789ABCDEF"
        temp_frac = fractional_part
        for _ in range(MAX_PRECISION):
            temp_frac *= to_base
            digit = int(temp_frac)
            frac_str += hex_digits[digit]
            temp_frac -= digit
            if temp_frac < 1e-9:
                break
    return f"{sign}{int_str}.{frac_str}".rstrip('.')

@app.route("/", methods=["GET", "POST"])
def index():
    bases = [(10, "Decimal"), (2, "Binary"), (8, "Octal"), (16, "Hexadecimal")]
    context = {
        "bases": bases,
        "error": None,
        "results": None,
        "number": "",
        "number2": "",
        "base_in": 10,
        "operation": "convert"
    }
    if request.method == "POST":
        context.update({
            "number": request.form.get("number", ""),
            "number2": request.form.get("number2", ""),
            "base_in": int(request.form.get("base_in", 10)),
            "operation": request.form.get("operation", "convert")
        })
        try:
            dec_value1, error = validate_and_parse(context["number"], context["base_in"])
            if error:
                context["error"] = f"First Number Error: {error}"
                return render_template_string(HTML_TEMPLATE, **context)
            dec_value2 = 0
            if context["operation"] in ('add', 'subtract'):
                dec_value2, error = validate_and_parse(context["number2"], context["base_in"])
                if error:
                    context["error"] = f"Second Number Error: {error}"
                    return render_template_string(HTML_TEMPLATE, **context)
            if context["operation"] == "add":
                dec_result = dec_value1 + dec_value2
            elif context["operation"] == "subtract":
                dec_result = dec_value1 - dec_value2
            else:
                dec_result = dec_value1
            results = {
                "decimal": format_from_decimal(dec_result, 10),
                "binary": format_from_decimal(dec_result, 2),
                "octal": format_from_decimal(dec_result, 8),
                "hex": format_from_decimal(dec_result, 16),
            }
            is_non_negative_integer = dec_result >= 0 and dec_result == int(dec_result)
            if is_non_negative_integer:
                int_val = int(dec_result)
                bin_str_unpadded = bin(int_val)[2:]
                padded_len = (len(bin_str_unpadded) + 7) // 8 * 8 if bin_str_unpadded else 8
                bin_str_padded = bin_str_unpadded.zfill(padded_len)
                results["ones_complement"] = ones_complement(bin_str_padded)
                results["twos_complement"] = twos_complement(bin_str_padded)
                decimal_int_str = str(int_val)
                results["bcd"] = decimal_to_bcd(decimal_int_str)
                results["gray"] = decimal_to_gray(int_val)
                results["excess3"] = decimal_to_excess_3(decimal_int_str)
            context["results"] = results
        except Exception as e:
            logging.error(f"An unhandled exception occurred: {e}", exc_info=True)
            context["error"] = "A critical server error occurred. Please try again."
    return render_template_string(HTML_TEMPLATE, **context)

if __name__ == "__main__":
    app.run(debug=True, port=5001)

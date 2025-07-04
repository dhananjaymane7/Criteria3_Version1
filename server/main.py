from flask import Flask, request, jsonify
import pandas as pd
from io import BytesIO
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def process_marks(input_file):
    df = pd.read_excel(input_file)

    if 'UT1' in df.columns:
        df['UT1'] = pd.to_numeric(df['UT1'], errors='coerce').fillna(0)
        df[['CO1_UT', 'CO2_UT']] = df['UT1'].apply(lambda x: pd.Series([x / 2, x / 2]))

    if 'UT2' in df.columns:
        df['UT2'] = pd.to_numeric(df['UT2'], errors='coerce').fillna(0)
        df[['CO3_UT', 'CO4_UT']] = df['UT2'].apply(lambda x: pd.Series([x / 2, x / 2]))

    if 'Prelim' in df.columns:
        df['Prelim'] = pd.to_numeric(df['Prelim'], errors='coerce').fillna(0)
        df[['CO3_P', 'CO4_P', 'CO5_P', 'CO6_P']] = df['Prelim'].apply(lambda x: pd.Series([x / 4, x / 4, x / 4, x / 4]))

    if 'Insem' in df.columns:
        df['Insem'] = pd.to_numeric(df['Insem'], errors='coerce').fillna(0)
        df[['CO1_I', 'CO2_I']] = df['Insem'].apply(lambda x: pd.Series([x / 2, x / 2]))

    if 'Endsem' in df.columns:
        df['Endsem'] = pd.to_numeric(df['Endsem'], errors='coerce').fillna(0)
        df[['CO3_E', 'CO4_E', 'CO5_E', 'CO6_E']] = df['Endsem'].apply(lambda x: pd.Series([x / 4, x / 4, x / 4, x / 4]))

    results = {}
    columns_and_totals = {
        'CO1_UT': 15, 'CO2_UT': 15, 'CO3_UT': 15, 'CO4_UT': 15,
        'CO3_P': 17.5, 'CO4_P': 17.5, 'CO5_P': 17.5, 'CO6_P': 17.5,
        'CO1_I': 15, 'CO2_I': 15, 'CO3_E': 17.5, 'CO4_E': 17.5, 'CO5_E': 17.5, 'CO6_E': 17.5
    }

    for column, total in columns_and_totals.items():
        if column in df.columns:
            percentage = (df[column] / total) * 100

        # Granular logic for score calculation
            def calculate_score(p):
                if p < 51:
                    # return p / 60  # Scale percentage 0-60 to range 0-1
                    return 0
                elif 51 <= p < 61:
                    # return 1 + (p - 60) / 10  # Scale percentage 61-70 to range 1-2
                    return 1
                elif 61 <= p < 71:
                    # return 2 + (p - 70) / 10  # Scale percentage 71-80 to range 2-3
                    return 2
                else:
                    return 3  # Above 80 gets 3

        scores = percentage.apply(calculate_score)
        results[column] = {
            "percentage": percentage.tolist(),
            "scores": scores.tolist(),
        }

# Calculate attainment
    total_students = len(df)
    attainment = {
        column: scores.sum() / total_students if column in results else None
        for column, scores in ((col, pd.Series(res["scores"])) for col, res in results.items())
    }
    co1 = (attainment.get('CO1_I', 0) * 0.8) + (attainment.get('CO1_UT', 0) * 0.2)
    co2 = (attainment.get('CO2_I', 0) * 0.8) + (attainment.get('CO2_UT', 0) * 0.2)
    co3 = (attainment.get('CO3_UT', 0) * 0.2) + (attainment.get('CO3_P', 0) * 0.2) + (attainment.get('CO3_E', 0) * 0.6)
    co4 = (attainment.get('CO4_UT', 0) * 0.2) + (attainment.get('CO4_P', 0) * 0.2) + (attainment.get('CO4_E', 0) * 0.6)
    co5 = (attainment.get('CO5_P', 0) * 0.2) + (attainment.get('CO5_E', 0) * 0.8)
    co6 = (attainment.get('CO6_P', 0) * 0.2) + (attainment.get('CO6_E', 0) * 0.8)

    co_values = {"CO1": co1, "CO2": co2, "CO3": co3, "CO4": co4, "CO5": co5, "CO6": co6}    

    return co_values, attainment

def process_practical_marks(marks, co_count):
    for i in range(1, co_count + 1):
        col_name = f'CO{i}'
        if 'TW' in marks.columns and 'OR' in marks.columns:
            print('TW OR')
            marks[col_name] = ((marks['TW']*0.2)+(marks['OR']*0.8))/ co_count
        elif 'TW' in marks.columns and 'PR' in marks.columns:
            print('TW PR')
            marks[col_name] = ((marks['TW']*0.2)+(marks['PR']*0.8))/ co_count
        elif 'TW' in marks.columns:
            print('TW')
            marks[col_name] = marks['TW'] / co_count
    print(marks)
    return marks

def calculate_average(df):
    co_columns = ['CO1', 'CO2', 'CO3', 'CO4', 'CO5', 'CO6']
    return df[co_columns].mean().to_dict()

def calculate_po_values(matrix, co_inputs):
    df = pd.DataFrame(matrix)
    po_results = {}
    for index in range(df.shape[1]):
        weighted_sum = sum(df.iloc[i, index] * co_inputs[i] for i in range(6) if not pd.isna(df.iloc[i, index]))
        weighted_components = sum(df.iloc[i, index] for i in range(6) if not pd.isna(df.iloc[i, index]))
        po_value = weighted_sum / weighted_components if weighted_components != 0 else 0
        po_results[f"PO{index + 1}"] = po_value
    return po_results


@app.route('/direct-process', methods=['POST'])
def process_direct_file():
    # Get the uploaded file
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file provided"}), 400

    # Parse matrix JSON from request body
    matrix = request.form.get('matrix') or request.json.get('matrix')


    if not matrix:
        return jsonify({"error": "Matrix data missing"}), 400

    try:
        if isinstance(matrix, str):  # Handle matrix if it's a string from form-data
            matrix = eval(matrix)
    except:
        return jsonify({"error": "Invalid matrix format"}), 400

    # Read the file and process it
    input_file = BytesIO(file.read())
    print(input_file)
    df = pd.read_excel(input_file)
    co_values, po_values = {}, []
    if any(col in df.columns for col in ['UT1', 'UT2', 'Prelim', 'Insem', 'Endsem']):
        co_values, _ = process_marks(input_file)
    elif any(col in df.columns for col in ['CO1', 'CO2', 'CO3', 'CO4', 'CO5', 'CO6']):
        co_values = calculate_average(df)
    elif any(col in df.columns for col in ['TW']):
        marks = process_practical_marks(df, co_count=6)
        co_values = calculate_average(marks)

    if co_values:
        co_inputs = [co_values.get(f"CO{i}", 0) for i in range(1, 7)]
        po_values = calculate_po_values(matrix, co_inputs)
    return jsonify({"co_values": co_values, "po_values": po_values})

@app.route('/indirect-process', methods=['POST'])
def process_indirect_file():
    # Get the uploaded file
    file = request.files.get('file')
    matrix = request.form.get('matrix') or request.json.get('matrix')
    if isinstance(matrix, str):  # Handle matrix if it's a string from form-data
        matrix = eval(matrix)
    if not file:
        return jsonify({"error": "No file provided"}), 400

    try:
        # Read the file into a DataFrame
        input_file = BytesIO(file.read())
        if not file.filename.endswith(('.xls', '.xlsx')):
            return jsonify({"error": "Unsupported file type. Please upload an Excel file."}), 415

        df = pd.read_excel(input_file)
        print(df)

        # Ensure the required columns are present
        required_columns = ['CO1', 'CO2', 'CO3', 'CO4', 'CO5', 'CO6']
        if not all(col in df.columns for col in required_columns):
            return jsonify({"error": f"Missing required columns. Expected columns: {', '.join(required_columns)}"}), 400

        # Calculate CO values as the mean of each column
        co_values = df[required_columns].mean().to_dict()
        print("CO values", list(co_values.values()))
        print("matrix", matrix)

        # Example PO calculation based on CO values (dummy logic)
        # po_values = {f"PO{i+1}": sum(co_values.values()) * (i+1) / 100 for i in range(12)}
        po_values = calculate_po_values(matrix, list(co_values.values()))
        print(po_values)
        # Map PSO1, PSO2, PSO3 to PO13, PO14, PO15
        po_values.update({
            "PSO1": po_values.get("PO13", 0),
            "PSO2": po_values.get("PO14", 0),
            "PSO3": po_values.get("PO15", 0),
        })
        print(po_values)

        return jsonify({"co_values": co_values, "po_values": po_values})
    except Exception as e:
        return jsonify({"error": f"Failed to process the file: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

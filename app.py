from flask import Flask, render_template, request
import locale

app = Flask(__name__)

# Helper to format currency
def format_currency(value):
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return value

def format_number(value):
    try:
        return f"{int(float(value)):,}".replace(",", ".")
    except:
        return value

app.jinja_env.filters['currency'] = format_currency
app.jinja_env.filters['number'] = format_number

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/report', methods=['POST'])
def report():
    # --- Head Office Inputs (AI) ---
    setup_fee = float(request.form.get('setup_fee', 0))
    monthly_sub = float(request.form.get('monthly_sub', 0))
    cost_per_msg = float(request.form.get('cost_per_msg', 0))
    
    # --- Client Inputs (Human) ---
    num_agents = float(request.form.get('num_agents', 1))
    salary_monthly = float(request.form.get('salary_monthly', 0))
    social_charges_rate = float(request.form.get('social_charges_rate', 40)) / 100
    benefits_monthly = float(request.form.get('benefits_monthly', 0))
    mgmt_fee_rate = float(request.form.get('mgmt_fee_rate', 8)) / 100
    platform_cost_monthly = float(request.form.get('platform_cost_monthly', 0))
    
    work_days_month = float(request.form.get('work_days_month', 22))
    interactions_per_day = float(request.form.get('interactions_per_day', 48))
    
    # --- CALCULATIONS: HUMAN (PER AGENT) ---
    # 1. Annual Base Salary
    annual_salary = salary_monthly * 12
    
    # 2. Provisions (Excel factor 1.665 on monthly salary? Or is it 1.665 months worth?)
    # Analysis showed: B22 = B4 * 1.665. B4 is Monthly Salary.
    # So Annual Provisions field = Monthly * 1.665.
    # Note: 1.665 * 2500 = 4162. This seems very low for Annual Provisions if it covers 13th + Vac.
    # Standard usually: (13th + 1/3 vac + vac) ~ 2.33 salaries.
    # However, I must stick to the Excel logic: Provisions = Monthly * 1.665.
    annual_provisions = salary_monthly * 1.665
    
    # 3. Total Salary Base
    total_base_salary = annual_salary + annual_provisions
    
    # 4. Social Charges (On Total Base)
    annual_social_charges = total_base_salary * social_charges_rate
    
    # 5. Management Cost (On Annual Salary ONLY per Excel B25=B21*B7)
    annual_mgmt_cost = annual_salary * mgmt_fee_rate
    
    # 6. Platform Cost (Annual)
    annual_platform = platform_cost_monthly * 12
    
    # 7. Benefits (Annual)
    annual_benefits = benefits_monthly * 12
    
    # 8. TOTAL ANNUAL COST PER AGENT (CTA)
    # Excel B28: Sal/Prov + Charges + Benefits + Mgmt + Platform
    cta_per_agent = total_base_salary + annual_social_charges + annual_benefits + annual_mgmt_cost + annual_platform
    
    # Total Human Cost (All Agents)
    total_human_cost_annual = cta_per_agent * num_agents
    total_human_cost_monthly = total_human_cost_annual / 12
    
    # Productivity (Volume)
    interactions_per_agent_monthly = interactions_per_day * work_days_month
    interactions_per_agent_annual = interactions_per_agent_monthly * 12
    
    total_interactions_annual = interactions_per_agent_annual * num_agents
    
    cost_per_interaction_human = total_human_cost_annual / total_interactions_annual if total_interactions_annual else 0
    
    # --- CALCULATIONS: AI (HEAD OFFICE) ---
    # Volume Assumption: AI handles ALL interactions
    ai_volume_annual = total_interactions_annual
    ai_volume_monthly = total_interactions_annual / 12
    
    # Variable Cost
    ai_variable_monthly = ai_volume_monthly * cost_per_msg
    ai_variable_annual = ai_variable_monthly * 12
    
    # Fixed Cost
    ai_fixed_annual = monthly_sub * 12
    
    # Total AI Operational Cost (Annual)
    ai_opex_annual = ai_fixed_annual + ai_variable_annual
    
    # Total AI Investment Year 1 (with Setup)
    ai_total_y1 = setup_fee + ai_opex_annual
    
    # --- ROI METRICS ---
    savings_annual = total_human_cost_annual - ai_opex_annual
    savings_y1 = total_human_cost_annual - ai_total_y1
    
    roi_percentage = (savings_y1 / ai_total_y1 * 100) if ai_total_y1 > 0 else 0
    
    # Payback Calculation
    # Monthly Cash Flow
    # Month 0: -Setup
    # Month 1..12: Savings/Month - AI_Cost/Month
    
    monthly_savings = total_human_cost_monthly - (ai_opex_annual / 12)
    cumulative = -setup_fee
    payback_month = "Immediate" if cumulative >= 0 else "> 12 months"
    
    chart_labels = ["Mês 1", "Mês 2", "Mês 3", "Mês 4", "Mês 5", "Mês 6", "Mês 7", "Mês 8", "Mês 9", "Mês 10", "Mês 11", "Mês 12"]
    chart_human_cumulative = []
    chart_ai_cumulative = []
    
    curr_human = 0
    curr_ai = setup_fee
    
    for _ in range(12):
        curr_human += total_human_cost_monthly
        curr_ai += (ai_opex_annual / 12)
        
        chart_human_cumulative.append(round(curr_human, 2))
        chart_ai_cumulative.append(round(curr_ai, 2))
        
        # Check payback
        if payback_month == "> 12 months" and curr_human >= curr_ai:
             payback_month = f"{_ + 1} meses"

    # Calculate bar height percentage for UI
    ai_bar_height_val = (ai_opex_annual / total_human_cost_annual * 100) if total_human_cost_annual > 0 else 0
    ai_bar_style = f"height: {ai_bar_height_val}%;"

    # Context for template
    context = {
        # Inputs echoing
        "inputs": request.form,
        
        # Results
        "total_human_annual": total_human_cost_annual,
        "cost_per_interaction_human": cost_per_interaction_human,
        "total_ai_annual_opex": ai_opex_annual,
        "total_ai_y1": ai_total_y1,
        "savings_y1": savings_y1,
        "roi_percentage": roi_percentage,
        "payback_month": payback_month,
        
        # Chart Data
        # Chart Data
        "ai_bar_height": ai_bar_height_val,
        "chart_payload": {
            "labels": chart_labels,
            "human": chart_human_cumulative,
            "ai": chart_ai_cumulative
        }
    }
    
    return render_template('report.html', **context)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

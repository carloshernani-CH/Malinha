import os
import requests
from dotenv import load_dotenv
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from flask import Flask, request, jsonify

app = Flask(__name__)

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Obter variáveis de ambiente
shopify_url = os.getenv("SHOPIFY_URL")
shopify_access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
email_from = os.getenv("EMAIL_FROM")
email_to = os.getenv("EMAIL_TO")
smtp_password = os.getenv("SMTP_PASSWORD")

# Criar o header de autenticação usando token de acesso
auth_header = {
    'Content-Type': 'application/json',
    'X-Shopify-Access-Token': shopify_access_token
}

def get_all_products():
    products = []
    try:
        url = f'https://{shopify_url}/admin/api/2024-04/products.json'
        params = {'limit': 250}
        while url:
            response = requests.get(url, headers=auth_header, params=params)
            response.raise_for_status()
            data = response.json()
            products.extend(data.get('products', []))
            url = response.links.get('next', {}).get('url')
            params = {}
        return products
    except requests.exceptions.RequestException as e:
        print(f'Error fetching products: {e}')
        return []

def filter_products_by_tags(products, style, occasion):
    filtered_products = []
    for product in products:
        product_tags = set(product.get('tags', '').split(', '))
        if 'Novidade' in product_tags and (style in product_tags or occasion in product_tags):
            filtered_products.append(product)
    return filtered_products

def create_box(style, occasion):
    all_products = get_all_products()
    products = filter_products_by_tags(all_products, style, occasion)

    if not products:
        print('No products found for the given tags.')
        return None

    box = {
        'products': products,
        'style': style,
        'occasion': occasion,
    }

    print('Custom box created:', box)
    pdf_filename = create_pdf(box['products'])
    return pdf_filename

def create_pdf(products):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Product Box", ln=True, align='C')

    for product in products:
        pdf.ln(10)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Product: {product['title']}", ln=True, align='L')
        
        for variant in product['variants']:
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 10, txt=f"Size: {variant['option1']}, Color: {variant['option2']}", ln=True, align='L')

        if 'image' in product and product['image']:
            image_url = product['image']['src']
            response = requests.get(image_url)
            image_file = f"{product['id']}.jpg"
            with open(image_file, "wb") as file:
                file.write(response.content)
            pdf.image(image_file, x=10, y=None, w=100)
            os.remove(image_file)

    pdf_filename = "product_box.pdf"
    pdf.output(pdf_filename)
    print("PDF created successfully!")
    return pdf_filename

def send_email_with_pdf(pdf_filename, form_data):
    corpo_email = f"""
    Olá,

    Por favor, encontre em anexo o PDF da caixa de produtos.

    Informações do Formulário:
    Nome: {form_data['nome']}
    Telefone com DDD: {form_data['telefone_ddd']}
    Email: {form_data['email']}
    Tamanho de Roupas: {form_data['tamanho_roupas']}
    Tamanho de Pijamas: {form_data['tamanho_pijamas']}
    CEP: {form_data['cep']}
    Número: {form_data['numero']}
    Número da Unidade: {form_data['numero_unidade']}

    Atenciosamente,
    Sua Empresa
    """

    msg = MIMEMultipart()
    msg['Subject'] = "PDF da Caixa de Produtos"
    msg['From'] = email_from
    msg['To'] = email_to

    msg.attach(MIMEText(corpo_email, 'plain'))

    with open(pdf_filename, "rb") as attachment:
        part = MIMEApplication(attachment.read(), Name=os.path.basename(pdf_filename))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_filename)}"'
        msg.attach(part)

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(email_from, smtp_password)
        server.sendmail(email_from, email_to, msg.as_string())
    
    print('Email enviado')

@app.route('/submit_form', methods=['POST'])
def submit_form():
    try:
        form_data = request.json
        print(f"Received form data: {form_data}")
        
        pdf_filename = create_box(form_data['estilos_preferidos'], form_data['ocasioes'])
        
        if pdf_filename:
            send_email_with_pdf(pdf_filename, form_data)
            return jsonify({"message": "Formulário processado com sucesso e email enviado."}), 200
        else:
            return jsonify({"message": "Nenhum produto encontrado para os critérios fornecidos."}), 404
    except Exception as e:
        print(f"Error processing form: {e}")
        return jsonify({"message": "Ocorreu um erro ao processar o formulário."}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

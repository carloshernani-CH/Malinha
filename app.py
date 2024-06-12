import os
import requests
from dotenv import load_dotenv
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Obter variáveis de ambiente
shopify_url = os.getenv("SHOPIFY_URL")
shopify_api_key = os.getenv("SHOPIFY_API_KEY")
shopify_password = os.getenv("SHOPIFY_PASSWORD")
shopify_access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")  # Novo: token de acesso
email_from = os.getenv("EMAIL_FROM")
email_to = os.getenv("EMAIL_TO")
smtp_password = os.getenv("SMTP_PASSWORD")

# Debug: verificar se as variáveis de ambiente estão sendo carregadas corretamente
print(f'Shopify URL: {shopify_url}')
print(f'Shopify API Key: {shopify_api_key}')
print(f'Shopify Password: {shopify_password}')
print(f'Shopify Access Token: {shopify_access_token}')
print(f'Email From: {email_from}')
print(f'Email To: {email_to}')
print(f'SMTP Password: {smtp_password}')

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
            # Pega o link para a próxima página
            url = response.links.get('next', {}).get('url')
            params = {}  # Limpa os params após a primeira solicitação
        return products
    except requests.exceptions.RequestException as e:
        print(f'Error fetching products: {e}')
        return []

def filter_products_by_tags(products, style, occasion):
    filtered_products = []
    for product in products:
        product_tags = set(product.get('tags', '').split(', '))
        if 'Novidade' in product_tags and (style in product_tags and occasion in product_tags):
            filtered_products.append(product)
    return filtered_products

def create_box(style, occasion):
    all_products = get_all_products()
    products = filter_products_by_tags(all_products, style, occasion)

    if not products:
        print('No products found for the given tags.')
        return

    box = {
        'products': products,  # Inclui todos os produtos filtrados
        'style': style,
        'occasion': occasion,
    }

    print('Custom box created:', box)
    pdf_filename = create_pdf(box['products'])
    send_email_with_pdf(pdf_filename)
    return box

def create_pdf(products):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Product Box", ln=True, align='C')

    # Títulos das colunas
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(40, 10, "Product", 1)
    pdf.cell(30, 10, "Variant", 1)
    pdf.cell(30, 10, "Size", 1)
    pdf.cell(30, 10, "Color", 1)
    pdf.cell(30, 10, "Price", 1)
    pdf.ln()

    # Dados dos produtos
    for product in products:
        pdf.set_font("Arial", size=12)
        for variant in product['variants']:
            pdf.cell(40, 10, product['title'], 1)
            pdf.cell(30, 10, variant['title'], 1)
            pdf.cell(30, 10, variant['option1'] or '', 1)
            pdf.cell(30, 10, variant['option2'] or '', 1)
            pdf.cell(30, 10, f"${variant['price']}", 1)
            pdf.ln()

        if 'image' in product and product['image']:
            image_url = product['image']['src']
            response = requests.get(image_url)
            image_file = f"{product['id']}.jpg"
            with open(image_file, "wb") as file:
                file.write(response.content)
            pdf.image(image_file, x=10, y=None, w=100)
            os.remove(image_file)
            pdf.ln(10)

    pdf_filename = "product_box.pdf"
    pdf.output(pdf_filename)
    print("PDF created successfully!")
    return pdf_filename

def send_email_with_pdf(pdf_filename):
    corpo_email = """
    Olá,
    
    Por favor, encontre em anexo o PDF da caixa de produtos.
    
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

# Exemplo de chamada da função com strings de estilo e ocasião
style = 'Casual'
occasion = 'Verão'

create_box(style, occasion)


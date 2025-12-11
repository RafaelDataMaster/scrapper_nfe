import pdfplumber

arquivo = "nfs/nsfe_contaazul_salvador.pdf"

with pdfplumber.open(arquivo) as pdf:
    # Pega a primeira página
    pagina = pdf.pages[0]
    
    # Cria uma imagem da página (precisa da lib Pillow/PIL instalada, o pdfplumber já traz)
    im = pagina.to_image(resolution=150)
    
    # 1. Desenha caixas vermelhas em volta de cada PALAVRA encontrada
    im.draw_rects(pagina.extract_words(), stroke="red", stroke_width=1)
    
    # 2. Desenha linhas azuis onde ele detecta LINHAS GRÁFICAS (bordas de tabela)
    im.draw_lines(pagina.lines, stroke="blue", stroke_width=2)
    
    # Salva para você olhar
    im.save("raio_x_nf_2.png")

print("Imagem de debug salva como 'raio_x_nf.png'. Abra para analisar.")
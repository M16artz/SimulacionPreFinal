"""Exporta el artículo integrado a un único LaTeX, con gráficos vectoriales."""
from pathlib import Path
import json
import re
from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

RAIZ = Path(__file__).resolve().parents[2]
DOCUMENTO = Document(RAIZ / 'documentacion/edicion_informe/InformeFinalSimulacion(2)_integrado.docx')
DATOS = json.loads((RAIZ / 'documentacion/analisis_informe/analisis_verificado.json').read_text(encoding='utf-8'))['fuentes']['E3']['filas']
INDICE = {tuple(int(f[k]) for k in ('mesas', 'meseros', 'cocineras')): f for f in DATOS}

def escapar(texto):
    reemplazos = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}', 'λ': r'\(\lambda\)', 'ᵢ': r'\textsubscript{i}', 'ᵣ': r'\textsubscript{r}', '−': '-', '×': r'\(\times\)', '≤': r'\(\leq\)', '≥': r'\(\geq\)'}
    texto = ''.join(reemplazos.get(c, c) for c in texto)
    texto = re.sub(r'\[(\d+)\]', r'\\cite{ref\1}', texto)
    return texto.replace('\n', r'\newline ')

salida = [r'''% !TeX program = xelatex
% Archivo autocontenido: tablas, bibliografía y figuras se definen aquí.
% Compilar dos veces con XeLaTeX (también admite LuaLaTeX o pdfLaTeX).
% En Overleaf: subir este archivo y seleccionar XeLaTeX.
% Fuente: InformeFinalSimulacion(2).docx y propuesta de secciones 6.4 a 10.
% Los experimentos históricos corresponden a datos sintéticos del modelo 1.0.0.
\documentclass[10pt,a4paper,twocolumn]{article}
\usepackage{iftex}
\ifPDFTeX
  \usepackage[utf8]{inputenc}
  \usepackage[T1]{fontenc}
  \usepackage{newtxtext,newtxmath}
\else
  \usepackage{fontspec}
  \setmainfont{TeX Gyre Termes}
  \usepackage{amsmath,amssymb}
\fi
\usepackage[spanish,es-tabla]{babel}
\usepackage[margin=1.7cm,top=1.9cm,bottom=1.9cm]{geometry}
\usepackage{booktabs,tabularx,array,graphicx,microtype}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usepackage{dblfloatfix}
\usepackage[hyphens]{url}
\usepackage[hidelinks]{hyperref}
\urlstyle{same}
\setlength{\columnsep}{0.65cm}
\setlength{\emergencystretch}{2em}
\renewcommand{\thesection}{\Roman{section}}
\renewcommand{\thesubsection}{\Alph{subsection}}
\renewcommand{\thesubsubsection}{\arabic{subsubsection}}
\renewcommand{\thetable}{\Roman{table}}
\newcolumntype{Y}{>{\raggedright\arraybackslash}X}
\definecolor{verde}{HTML}{27665C}
\definecolor{azul}{HTML}{3E6B96}
\definecolor{naranja}{HTML}{C08332}
\pgfplotsset{informe/.style={width=.94\textwidth,height=6.4cm,
  tick label style={font=\small},label style={font=\small},
  legend style={font=\small,draw=none,at={(.5,1.06)},anchor=south,legend columns=-1},
  ymajorgrids=true,grid style={gray!20},axis lines*=left}}
''']
salida.append(r'\title{' + escapar(DOCUMENTO.paragraphs[0].text) + '}')
autores = [c.text.splitlines() for c in DOCUMENTO.tables[0].rows[0].cells]
salida.append(r'\author{' + r' \and '.join(r'\begin{tabular}{c}' + r'\\'.join(escapar(x) for x in a[:3]) + r'\\\small\texttt{' + escapar(a[3]) + r'}\end{tabular}' for a in autores) + '}')
salida.append(r'\date{}' + '\n' + r'\begin{document}' + '\n' + r'\maketitle')

FORMULAS = [
 r'\lambda(t)=\begin{cases}20,&12\leq t<14\ \text{o}\ 18\leq t<20,\\8,&\text{en el resto de la admisión}.\end{cases}',
 None,
 r'U_r=\frac{T_{\mathrm{ocupado},r}}{c_r T}\,100\%',
 r'\overline W_{q,i}=\frac{1}{n_i}\sum_{k=1}^{n_i}W_{q,i,k}',
 r'\overline L_{q,i}=\frac{1}{T}\int_0^T Q_i(t)\,\mathrm dt',
 r'W_{\mathrm{total},k}=t_{\mathrm{salida},k}-t_{\mathrm{llegada},k}',
 r'P_{\mathrm{aband}}=\frac{N_{\mathrm{aband}}}{N_{\mathrm{llegadas}}}\,100\%',
 r'L=\lambda_{\mathrm{ef}}W',
 r'\overline x\ \pm\ t_{0.975,n-1}\frac{s}{\sqrt n}',
 r'\left(M,S,C,\overline P_{\mathrm{aband}},\overline W_{\mathrm{mesa}}\right)',
]
simbolos = [r'$\lambda(t)$', r'$G$', r'$T_{\mathrm{pedido}}$', r'$T_{\mathrm{preparacion}}$', r'$T_{\mathrm{entrega}}$', r'$T_{\mathrm{consumo}}$', r'$T_{\mathrm{cobro}}$', r'$P$', r'$M$', r'$S$', r'$C$', r'$\overline W_{q,i}$', r'$\overline L_{q,i}$', r'$\overline W_{\mathrm{total}}$', r'$U_r$', r'$N_{\mathrm{atendidos}}$', r'$N_{\mathrm{aband}}$']
numero_tabla = 0
numero_figura = 0
numero_formula = 0
titulo_tabla = ''
bibliografia = False
omitir_leyenda = False

def figura(numero):
    comunes = r'xlabel={Configuración: mesas/meseros/cocineras},ymin=0,'
    if numero in (1, 3):
        claves = [(11,1,3),(13,2,4),(13,3,5),(13,3,6)] + ([(13,3,7)] if numero == 1 else [])
        etiquetas = ','.join('/'.join(map(str,c)) for c in claves)
        opciones = comunes + f'symbolic x coords={{{etiquetas}}},xtick=data,'
        if numero == 1:
            opciones += r'ybar,bar width=23pt,ymax=80,ylabel={Permanencia (minutos)},nodes near coords,point meta=y,every node near coord/.append style={font=\scriptsize},'
            columnas = [('tiempo_sistema_medio_media',1,'verde')]
        else:
            opciones += r'ybar,bar width=12pt,ymax=100,ylabel={Utilización (\%)},'
            columnas = [('utilizacion_mesa_media',100,'verde'),('utilizacion_mesero_media',100,'azul'),('utilizacion_cocinera_media',100,'naranja')]
        grafico = r'\begin{axis}[informe,'+opciones+']\n'
        for campo,escala,color in columnas:
            coordenadas = ' '.join('('+ '/'.join(map(str,c))+f',{INDICE[c][campo]*escala:.6f})' for c in claves)
            grafico += r'\addplot[fill='+color+',draw='+color+'] coordinates {'+coordenadas+'};\n'
        if numero == 3:
            grafico += r'\legend{Mesas,Meseros,Cocineras}'+'\n'
    else:
        grafico = r'\begin{axis}[informe,xlabel={Cantidad de cocineras},ylabel={Permanencia (minutos)},xmin=3,xmax=7,xtick={3,4,5,6,7},ymin=40,ymax=55,nodes near coords,every node near coord/.append style={font=\scriptsize}]'+'\n'
        coordenadas = ' '.join(f'({c},{INDICE[(13,3,c)]["tiempo_sistema_medio_media"]:.6f})' for c in range(3,8))
        grafico += r'\addplot[verde,thick,mark=*] coordinates {'+coordenadas+'};\n'
    grafico += r'\end{axis}'
    leyendas = {
      1:'Permanencia media de los grupos atendidos en configuraciones seleccionadas de E3. Medias de cinco réplicas con semillas comunes; datos sintéticos. Los intervalos se presentan en las tablas de resultados.',
      2:'Efecto de ampliar cocina con 13 mesas y tres meseros. El eje vertical comienza en 40 minutos para mostrar las diferencias. Fuente: E3, cinco réplicas por configuración.',
      3:'Utilización media por recurso durante la jornada completa, incluida la atención posterior al cierre. Fuente: E3, cinco réplicas por configuración; datos sintéticos.',
    }
    return '\n'+r'\begin{figure*}[!tb]\centering'+'\n'+r'\begin{tikzpicture}'+'\n'+grafico+'\n'+r'\end{tikzpicture}'+'\n'+r'\caption{'+escapar(leyendas[numero])+'}\n'+r'\label{fig:'+str(numero)+'}\n'+r'\end{figure*}'+'\n'

for elemento in DOCUMENTO.element.body:
    if elemento.tag == qn('w:tbl'):
        t = Table(elemento, DOCUMENTO._body)
        numero_tabla += 1
        if numero_tabla == 1:
            continue
        filas = [[c.text for c in r.cells] for r in t.rows]
        if numero_tabla == 3:
            for fila, simbolo in zip(filas[1:], simbolos):
                fila[0] = simbolo
        caption = re.sub(r'^Tabla [IVX]+\.\s*','', titulo_tabla).rstrip('.')
        salida.append(r'\begin{table*}[!tb]\centering\small'+'\n'+r'\caption{'+escapar(caption)+'}\n'+r'\label{tab:'+str(numero_tabla-1)+'}\n'+r'\setlength{\tabcolsep}{4pt}'+'\n'+r'\renewcommand{\arraystretch}{1.18}'+'\n'+r'\begin{tabularx}{\textwidth}{'+'Y'*len(filas[0])+'}\n'+r'\toprule')
        for i,fila in enumerate(filas):
            valores = [v if numero_tabla==3 and j==0 and i>0 else escapar(v) for j,v in enumerate(fila)]
            if i==0:
                valores = [r'\textbf{'+v+'}' for v in valores]
            salida.append(' & '.join(valores)+r' \\')
            if i==0:
                salida.append(r'\midrule')
        salida.append(r'\bottomrule\end{tabularx}\end{table*}'+'\n')
        continue
    if elemento.tag != qn('w:p'):
        continue
    p = Paragraph(elemento, DOCUMENTO._body)
    texto = p.text.strip()
    if p.style.name == 'Title':
        continue
    if elemento.findall('.//'+qn('w:drawing')):
        numero_figura += 1
        salida.append(figura(numero_figura))
        omitir_leyenda = True
        continue
    if elemento.findall('.//'+qn('m:oMath')):
        formula = FORMULAS[numero_formula]
        numero_formula += 1
        if formula:
            salida.append(r'\begin{equation}'+ '\n' +formula+'\n'+r'\end{equation}'+'\n')
        continue
    if not texto:
        continue
    if texto.startswith('Tabla '):
        titulo_tabla = texto
        continue
    if omitir_leyenda and texto.startswith('Figura '):
        omitir_leyenda = False
        continue
    if p.style.name.startswith('Heading'):
        if texto == 'REFERENCIAS':
            salida.append(r'\begin{thebibliography}{10}')
            bibliografia = True
            continue
        if bibliografia:
            salida.append(r'\end{thebibliography}')
            bibliografia = False
        nivel = int(p.style.name[-1])
        titulo = re.sub(r'^[A-G]\.\s*', '',texto) if nivel==2 else texto
        # La numeración de las etapas es parte del procedimiento, no del encabezado de subsección.
        if nivel==3 and not titulo.startswith('Etapa'):
            titulo = re.sub(r'^\d+\.\s*','',titulo)
        comando = {1:'section',2:'subsection',3:'subsubsection*'}[nivel]
        salida.append('\\'+comando+'{'+escapar(titulo)+'}\n')
        continue
    if bibliografia:
        coincidencia = re.match(r'^\[(\d+)\]\s*(.*)',texto)
        if coincidencia:
            contenido = escapar(coincidencia[2])
            doi = re.search(r'doi:\s*([^\s]+)\.?$',coincidencia[2])
            if doi:
                valor=doi[1].rstrip('.')
                contenido=contenido.replace(escapar(valor),r'\href{https://doi.org/'+valor+'}{'+escapar(valor)+'}')
            salida.append(r'\bibitem{ref'+coincidencia[1]+'} '+contenido+'\n')
        continue
    if texto.startswith('Resumen'):
        salida.append(r'\noindent\textbf{Resumen---} '+escapar(re.sub(r'^Resumen\s*[—–-]\s*','',texto))+'\n')
    elif texto.startswith(('Palabras Clave','Keywords')):
        salida.append(r'\noindent\textit{'+escapar(texto)+'}\n')
    else:
        # Se conservan los objetivos y se actualiza el relato de las fases ya realizadas.
        texto = texto.replace('ocupadas.Respecto','ocupadas. Respecto')
        salida.append(escapar(texto)+'\n')

salida.append(r'\end{document}'+'\n')
assert numero_figura == 3
assert numero_tabla == 12
assert numero_formula == len(FORMULAS), numero_formula
archivo=RAIZ/'InformeFinalSimulacion(2).tex'
archivo.write_text('\n'.join(salida),encoding='utf-8')
print(f'Creado: {archivo.name}; tablas: {numero_tabla-1}; figuras: {numero_figura}; ecuaciones: {numero_formula-1}')

# -*- coding: utf-8 -*-
"""
Gerador de Chaveiros para Claviculario
======================================

Desenvolvedor: Jesus Cavalcante de Assis Neto

Este arquivo concentra todo o programa em um unico lugar. A organizacao foi
mantida assim para facilitar a distribuicao e a manutencao por pessoas que nao
conhecem o projeto.

Ordem de leitura recomendada:
1. Configuracoes padrao do projeto.
2. Funcoes de validacao e calculo.
3. Contorno mestre extraido do AutoCAD.
4. Distribuicao das pecas na chapa.
5. Geracao de texto e QR Code.
6. Exportacao para DXF, PNG e PDF.
7. Interface grafica.

Regra importante:
O contorno de corte nao deve ser redesenhado por aproximacao. Os vertices e os
valores de bulge existentes em MODELO_AUTOCAD_DXF vieram do modelo aprovado no
AutoCAD e devem ser preservados.
"""
from __future__ import annotations
import json, math, re, tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ezdxf, qrcode
from PIL import Image, ImageDraw, ImageFont, ImageTk
from matplotlib.font_manager import FontProperties, findfont, fontManager
from matplotlib.textpath import TextPath
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader

BASE=Path(__file__).resolve().parent

# -----------------------------------------------------------------------------
# 1. CONFIGURACOES PADRAO
# -----------------------------------------------------------------------------
# Todos os valores que aparecem inicialmente na interface ficam nesta classe.
# Para mudar um valor padrao, altere apenas o numero correspondente abaixo.
@dataclass
class Cfg:
    nome:str='chaveiros_000_500'
    chapa_l:float=1000; chapa_a:float=1000; margem:float=5; espaco:float=1
    peca_l:float=41.4; peca_a:float=38.1; largura_base:float=38.9; raio_ext:float=2.5; raio_inf_esq:float=5.5; trecho_vertical_esq:float=24.9
    rasgo:bool=True; entrada_x:float=0.0; entrada_y:float=13.2; ponta_x:float=14.14; ponta_y:float=27.34
    largura_rasgo:float=4.4; raio_boca_sup:float=2.5; raio_boca_inf:float=2.5; raio_ponta:float=2.2
    furo:bool=True; furo_d:float=5.4; furo_x:float=11.2; furo_y:float=6.7
    texto:bool=True; inicial:int=0; final:int=500; digitos:int=3; prefixo:str=''; sufixo:str=''; fonte:str='Arial'; texto_h:float=5; texto_x:float=30; texto_y:float=29
    qr:bool=False; qr_texto:str='https://exemplo.local/{numero}'; qr_tamanho:float=12; qr_x:float=31; qr_y:float=11
    saida_dxf:bool=True; saida_png:bool=False; saida_pdf:bool=False; dpi:int=150
    def label(self,n):return f'{self.prefixo}{n:0{self.digitos}d}{self.sufixo}'

# -----------------------------------------------------------------------------
# 2. LEITURA, AJUSTE E VALIDACAO DOS CAMPOS
# -----------------------------------------------------------------------------
def fnum(v,n):
    """Converte um campo decimal e aceita virgula ou ponto."""
    try:return float(str(v).replace(',','.'))
    except:raise ValueError(f'O campo {n} precisa conter um número.')
def fint(v,n):
    """Converte um campo que deve conter somente numero inteiro."""
    try:return int(str(v))
    except:raise ValueError(f'O campo {n} precisa conter um número inteiro.')
def clamp(v,a,b):
    """Mantem um valor dentro dos limites minimo e maximo."""
    return max(a,min(b,v))
def ajustar(c):
    # Cotas funcionais do desenho técnico.
    c.entrada_y=c.peca_a-c.trecho_vertical_esq
    if c.furo:
        r=c.furo_d/2;c.furo_x=clamp(c.furo_x,r,c.peca_l-r);c.furo_y=clamp(c.furo_y,r,c.peca_a-r)
    c.texto_x=clamp(c.texto_x,0,c.peca_l);c.texto_y=clamp(c.texto_y,0,c.peca_a)
    if c.qr:
        q=c.qr_tamanho/2;c.qr_x=clamp(c.qr_x,q,c.peca_l-q);c.qr_y=clamp(c.qr_y,q,c.peca_a-q)
    return c
def validar(c):
    """Retorna uma lista com todos os problemas encontrados no projeto."""
    e=[]
    for n,v in [('largura da chapa',c.chapa_l),('altura da chapa',c.chapa_a),('largura da peça',c.peca_l),('altura da peça',c.peca_a)]:
        if v<=0:e.append(f'A {n} deve ser maior que zero.')
    if c.final<c.inicial:e.append('O número final não pode ser menor que o inicial.')
    if c.largura_base<=0 or c.largura_base>c.peca_l:e.append('A largura inferior deve ser maior que zero e menor ou igual à largura superior.')
    if c.trecho_vertical_esq<0 or c.trecho_vertical_esq>c.peca_a:e.append('O trecho vertical esquerdo deve ficar entre 0 e a altura total.')
    if c.margem<0 or c.espaco<0:e.append('Margem e espaçamento não podem ser negativos.')
    if not(c.saida_dxf or c.saida_png or c.saida_pdf):e.append('Marque ao menos um formato de saída.')
    if c.raio_ext<0 or c.raio_ext>min(c.peca_l,c.peca_a)/2:e.append('O raio externo é inválido.')
    if c.raio_inf_esq<0 or c.raio_inf_esq>min(c.peca_l,c.peca_a)/2:e.append('O raio inferior esquerdo é inválido.')
    if c.rasgo and min(c.largura_rasgo,c.raio_boca_sup,c.raio_boca_inf,c.raio_ponta)<0:e.append('As medidas da abertura não podem ser negativas.')
    return e

# -----------------------------------------------------------------------------
# 3. FUNCOES GEOMETRICAS AUXILIARES
# -----------------------------------------------------------------------------
# Estas funcoes criam arcos, curvas e pontos intermediarios usados na tela.
def arc(cx,cy,r,a1,a2,n=16):
    if r<=0:return [(cx,cy)]
    return [(cx+r*math.cos(math.radians(a1+(a2-a1)*i/n)),cy+r*math.sin(math.radians(a1+(a2-a1)*i/n))) for i in range(n+1)]
def qbez(a,b,c,n=10):
    return [((1-t)**2*a[0]+2*(1-t)*t*b[0]+t*t*c[0],(1-t)**2*a[1]+2*(1-t)*t*b[1]+t*t*c[1]) for t in [i/n for i in range(n+1)]]
def along(a,b,d):
    dx,dy=b[0]-a[0],b[1]-a[1];L=max(math.hypot(dx,dy),1e-9);k=min(1,d/L);return a[0]+dx*k,a[1]+dy*k

# -----------------------------------------------------------------------------
# 4. CONTORNO MESTRE DA PECA
# -----------------------------------------------------------------------------
# Cada item possui: coordenada X, coordenada Y e bulge do segmento seguinte.
# Bulge igual a zero representa linha reta. Bulge diferente de zero representa
# um arco. Evite arredondar ou alterar estes valores sem conferir no AutoCAD.
# Vertices mestres do AutoCAD no formato (X, Y, BULGE).
# Estes valores nao sao estimativas: foram extraidos do LWPOLYLINE final.
MODELO_AUTOCAD_DXF = [
    (2.500000000000, 5.500000000000, 0.0),
    (2.500000000000, 6.121407004848, -0.2313126300781743),
    (4.621180999324, 10.461174528653, 0.0),
    (16.063124805158, 19.369545063195, 0.4142135623730980),
    (16.499919588398, 22.877993483414, 0.0),
    (16.499919588398, 22.877993483414, 0.4142135623730953),
    (12.991471168180, 23.314788266654, 0.0),
    (1.614330727396, 14.456871780615, -0.6242828597259022),
    (0.000000000000, 15.245920421307, 0.0),
    (0.000000000000, 36.100000000000, -0.4142135623730951),
    (2.000000000000, 38.100000000000, 0.0),
    (39.400000000000, 38.100000000000, -0.4142135623730951),
    (41.400000000000, 36.100000000000, 0.0),
    (41.400000000000, 2.000000000000, -0.4142135623730951),
    (39.400000000000, 0.000000000000, 0.0),
    (8.000000000000, 0.000000000000, -0.4142135623730951),
]


def dxf_outline(c):
    """Retorna o contorno mestre exato para gravacao no DXF."""
    return MODELO_AUTOCAD_DXF


def _amostrar_bulge(p1, p2, bulge, segmentos=12):
    """Converte um segmento DXF com bulge em pontos apenas para a tela/PNG."""
    x1,y1=p1; x2,y2=p2
    if abs(bulge) < 1e-12:
        return [(x1,y1)]
    theta=4*math.atan(bulge)
    corda=math.hypot(x2-x1,y2-y1)
    raio=corda/(2*math.sin(abs(theta)/2))
    mx,my=(x1+x2)/2,(y1+y2)/2
    ux,uy=(x2-x1)/corda,(y2-y1)/corda
    nx,ny=-uy,ux
    distancia=corda/(2*math.tan(theta/2))
    cx,cy=mx+nx*distancia,my+ny*distancia
    a1=math.atan2(y1-cy,x1-cx)
    return [(cx+raio*math.cos(a1+theta*i/segmentos),
             cy+raio*math.sin(a1+theta*i/segmentos)) for i in range(segmentos)]


def outline(c):
    """Amostra o mesmo contorno mestre para pre-visualizacao e PNG."""
    vertices=dxf_outline(c)
    pontos=[]
    for i,(x,y,b) in enumerate(vertices):
        nx,ny,_=vertices[(i+1)%len(vertices)]
        pontos.extend(_amostrar_bulge((x,y),(nx,ny),b,14))
    return pontos

# -----------------------------------------------------------------------------
# 5. DISTRIBUICAO DAS PECAS NA CHAPA
# -----------------------------------------------------------------------------
def make_layouts(c):
    """Calcula quantas pecas cabem por linha, coluna e chapa."""
    cols=int(((c.chapa_l-2*c.margem)+c.espaco)//(c.peca_l+c.espaco));rows=int(((c.chapa_a-2*c.margem)+c.espaco)//(c.peca_a+c.espaco))
    if cols<1 or rows<1:raise ValueError('A peça não cabe na chapa.')
    cap=cols*rows;nums=list(range(c.inicial,c.final+1));out=[]
    for k in range(0,len(nums),cap):
        b=[]
        for i,n in enumerate(nums[k:k+cap]):b.append((n,c.margem+(i%cols)*(c.peca_l+c.espaco),c.margem+(i//cols)*(c.peca_a+c.espaco)))
        out.append(b)
    return out
# -----------------------------------------------------------------------------
# 6. TEXTO, NUMERACAO E QR CODE
# -----------------------------------------------------------------------------
def fontpath(n):return findfont(FontProperties(family=n),fallback_to_default=True)
def textpoly(t,font,h):
    """Transforma texto em contornos fechados para gravacao no DXF."""
    ps=TextPath((0,0),t,size=1,prop=FontProperties(fname=fontpath(font))).to_polygons()
    if not len(ps):return []
    xs=[x for a in ps for x in a[:,0]];ys=[y for a in ps for y in a[:,1]];s=h/max(max(ys)-min(ys),1e-9)
    return [[((x-min(xs))*s,(y-min(ys))*s) for x,y in a] for a in ps]
def qrmat(t):
    """Gera a matriz de quadrados claros e escuros do QR Code."""
    q=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=1,border=2);q.add_data(t);q.make(fit=True);return q.get_matrix()
def safe(s):
    """Remove caracteres que nao podem ser usados em nomes de arquivo."""
    return re.sub(r'[^A-Za-z0-9_.-]+','_',s) or 'chaveiros'

# -----------------------------------------------------------------------------
# 7. MONTAGEM E EXPORTACAO DOS ARQUIVOS
# -----------------------------------------------------------------------------
def put_piece(m,c,n,ox,oy):
    """Adiciona uma peca completa ao desenho DXF."""
    # O contorno usa os arcos originais do AutoCAD por meio do campo bulge.
    m.add_lwpolyline([(ox+x,oy+y,b) for x,y,b in dxf_outline(c)],format='xyb',close=True,dxfattribs={'layer':'01_CORTE'})
    if c.furo:m.add_circle((ox+c.furo_x,oy+c.furo_y),c.furo_d/2,dxfattribs={'layer':'02_FURO'})
    if c.texto:
        ps=textpoly(c.label(n),c.fonte,c.texto_h)
        if ps:
            xs=[x for a in ps for x,y in a];ys=[y for a in ps for x,y in a];dx=c.texto_x-(max(xs)-min(xs))/2;dy=c.texto_y-(max(ys)-min(ys))/2
            for a in ps:m.add_lwpolyline([(ox+dx+x,oy+dy+y) for x,y in a],close=True,dxfattribs={'layer':'03_TEXTO'})
    if c.qr:
        M=qrmat(c.qr_texto.replace('{numero}',c.label(n)));N=len(M);u=c.qr_tamanho/N;lx=c.qr_x-c.qr_tamanho/2;by=c.qr_y-c.qr_tamanho/2
        for r,row in enumerate(M):
            for col,on in enumerate(row):
                if on:
                    x=ox+lx+col*u;y=oy+by+(N-1-r)*u;m.add_lwpolyline([(x,y),(x+u,y),(x+u,y+u),(x,y+u)],close=True,dxfattribs={'layer':'04_QR'})

def export_dxf(c,L,chosen):
    """Cria um arquivo DXF para cada chapa calculada."""
    chosen=Path(chosen);base=safe(chosen.stem);A=[]
    for i,b in enumerate(L,1):
        doc=ezdxf.new('R2010');doc.units=4;m=doc.modelspace()
        for n,col in [('00_CHAPA',8),('01_CORTE',1),('02_FURO',1),('03_TEXTO',5),('04_QR',3)]:doc.layers.add(n,color=col)
        m.add_lwpolyline([(0,0),(c.chapa_l,0),(c.chapa_l,c.chapa_a),(0,c.chapa_a)],close=True,dxfattribs={'layer':'00_CHAPA'})
        for n,x,y in b:put_piece(m,c,n,x,y)
        suffix=f'_chapa_{i:03d}' if len(L)>1 else '';p=chosen.parent/f'{base}{suffix}.dxf';doc.saveas(p);A.append(p)
    return A

def render(c,b,p,dpi=90):
    """Cria a imagem usada na pre-visualizacao e no arquivo PNG."""
    s=max(.35,dpi/25.4);pad=16;W=int(c.chapa_l*s)+2*pad;H=int(c.chapa_a*s)+2*pad;im=Image.new('RGB',(W,H),'white');d=ImageDraw.Draw(im)
    def P(x,y):return pad+int(x*s),H-pad-int(y*s)
    d.rectangle([P(0,c.chapa_a),P(c.chapa_l,0)],outline='#777')
    try:f=ImageFont.truetype(fontpath(c.fonte),max(8,int(c.texto_h*s)))
    except:f=ImageFont.load_default()
    for n,ox,oy in b:
        d.polygon([P(ox+x,oy+y) for x,y in outline(c)],outline='#d32323')
        if c.furo:
            r=c.furo_d/2;d.ellipse([P(ox+c.furo_x-r,oy+c.furo_y+r),P(ox+c.furo_x+r,oy+c.furo_y-r)],outline='#d32323')
        if c.texto:
            t=c.label(n);bb=d.textbbox((0,0),t,font=f);x,y=P(ox+c.texto_x,oy+c.texto_y);d.text((x-(bb[2]-bb[0])/2,y-(bb[3]-bb[1])/2),t,font=f,fill='#1261b5')
    im.save(p);return p
def export_other(c,L,basepath):
    """Gera PNG e PDF quando esses formatos estiverem marcados."""
    A=[];imgs=[];stem=safe(Path(basepath).stem);folder=Path(basepath).parent
    if c.saida_png or c.saida_pdf:
        for i,b in enumerate(L,1):imgs.append(render(c,b,folder/f'{stem}_chapa_{i:03d}.png',c.dpi))
    if c.saida_png:A+=imgs
    if c.saida_pdf:
        p=folder/f'{stem}_conferencia.pdf';cv=pdfcanvas.Canvas(str(p),pagesize=landscape(A4));pw,ph=landscape(A4)
        for i,img in enumerate(imgs,1):
            cv.setFont('Helvetica-Bold',13);cv.drawString(30,ph-30,f'Chapa {i:03d}');im=Image.open(img);sc=min((pw-60)/im.width,(ph-65)/im.height);cv.drawImage(ImageReader(im),(pw-im.width*sc)/2,20,im.width*sc,im.height*sc);cv.showPage()
        cv.save();A.append(p)
        if not c.saida_png:
            for x in imgs:x.unlink(missing_ok=True)
    return A

# -----------------------------------------------------------------------------
# 8. INTERFACE GRAFICA
# -----------------------------------------------------------------------------
# A classe App cria a janela, le os campos, atualiza a visualizacao e chama as
# funcoes de exportacao. A geometria de corte continua separada nas funcoes
# anteriores para evitar que alteracoes visuais mudem o DXF por acidente.
class App(tk.Tk):
    def __init__(self):
        super().__init__();self.title('Gerador de Chaveiros para Claviculário V18 - modelo mestre AutoCAD');self.geometry('1320x850');self.minsize(1100,720);self.c=Cfg();self.v={};self.photo=None;self.changed=False;self.style();self.ui();self.load();self.after(350,self.preview)
    def style(self):
        s=ttk.Style(self)
        try:s.theme_use('vista')
        except:pass
        s.configure('Title.TLabel',font=('Segoe UI',18,'bold'));s.configure('Step.TLabelframe.Label',font=('Segoe UI',11,'bold'));s.configure('Primary.TButton',font=('Segoe UI',11,'bold'),padding=12)
    def var(self,n,t='s'):
        V={'s':tk.StringVar,'b':tk.BooleanVar}[t]();self.v[n]=V;V.trace_add('write',lambda *_:self.mark());return V
    def mark(self):self.changed=True
    def field(self,p,label,n,row):ttk.Label(p,text=label).grid(row=row,column=0,sticky='w',padx=7,pady=3);ttk.Entry(p,textvariable=self.var(n),width=14).grid(row=row,column=1,sticky='ew',padx=7,pady=3)
    def diagram(self,p,kind,rowspan=10):
        """Mini desenho técnico com linhas de extensão, cotas e setas."""
        C=tk.Canvas(p,width=390,height=285,bg='white',highlightthickness=1,highlightbackground='#b8b8b8')
        C.grid(row=0,column=3,rowspan=rowspan,padx=12,pady=5,sticky='n')
        vermelho='#c62828';azul='#1565c0';verde='#188038';cinza='#666'

        def seta_dim(x1,y1,x2,y2,texto,vertical=False):
            C.create_line(x1,y1,x2,y2,fill=azul,arrow='both',width=1)
            C.create_text((x1+x2)/2,(y1+y2)/2-8 if not vertical else (y1+y2)/2,
                          text=texto,fill=azul,angle=90 if vertical else 0)

        if kind=='shape':
            # Converte milímetros em pixels. Origem geométrica no canto inferior esquerdo.
            ex=Cfg();escala=4.45;ox=105;oy=225
            pts=[(ox+x*escala,oy-y*escala) for x,y in outline(ex)]
            C.create_polygon(pts,outline=vermelho,fill='',width=2)
            fx=ox+ex.furo_x*escala;fy=oy-ex.furo_y*escala;fr=ex.furo_d*escala/2
            C.create_oval(fx-fr,fy-fr,fx+fr,fy+fr,outline=vermelho,width=2)
            direita=ox+ex.peca_l*escala;direita_base=ox+ex.largura_base*escala;topo=oy-ex.peca_a*escala

            # Cota geral horizontal: largura total.
            ydim=22
            C.create_line(ox,topo,ox,ydim+5,fill=cinza)
            C.create_line(direita,topo,direita,ydim+5,fill=cinza)
            seta_dim(ox,ydim,direita,ydim,f'{ex.peca_l:.1f} mm')

            # Cota geral vertical: altura total.
            xdim=direita+28
            C.create_line(direita,topo,xdim-5,topo,fill=cinza)
            C.create_line(direita,oy,xdim-5,oy,fill=cinza)
            seta_dim(xdim,topo,xdim,oy,f'{ex.peca_a:.1f} mm',True)

            # Nova cota 24,9: topo até o centro da entrada lateral.
            yentrada=oy-ex.entrada_y*escala
            xdim2=ox-28
            C.create_line(ox,topo,xdim2+5,topo,fill=cinza)
            C.create_line(ox,yentrada,xdim2+5,yentrada,fill=cinza)
            seta_dim(xdim2,topo,xdim2,yentrada,f'{ex.trecho_vertical_esq:.1f} mm',True)

            # Nova cota 38,9: tangência inferior esquerda até a extremidade direita.
            xbase_inicio=ox+(ex.peca_l-ex.largura_base)*escala
            xbase_fim=ox+ex.peca_l*escala
            ydim2=oy+33
            C.create_line(xbase_inicio,oy,xbase_inicio,ydim2-5,fill=cinza)
            C.create_line(xbase_fim,oy,xbase_fim,ydim2-5,fill=cinza)
            seta_dim(xbase_inicio,ydim2,xbase_fim,ydim2,f'{ex.largura_base:.1f} mm')

            # Chamadas dos raios e da abertura.
            C.create_line(ox+5,yentrada-8,42,105,fill=verde,arrow='first')
            C.create_text(50,94,text='Raio superior',fill=verde)
            C.create_line(ox+5,yentrada+8,42,170,fill=verde,arrow='first')
            C.create_text(48,182,text='Raio inferior',fill=verde)
            C.create_line(ox+ex.ponta_x*escala,oy-ex.ponta_y*escala,322,96,fill=verde,arrow='first')
            C.create_text(335,87,text='Raio da ponta',fill=verde)
            C.create_line(ox-11,yentrada-10,ox-11,yentrada+10,fill=azul,arrow='both')
            C.create_text(ox-18,yentrada,text=f'{ex.largura_rasgo:.1f}',fill=azul,angle=90)
            C.create_line(ox+ex.raio_inf_esq*escala*0.30,oy-ex.raio_inf_esq*escala*0.30,42,240,fill=verde,arrow='first')
            C.create_text(62,250,text=f'R {ex.raio_inf_esq:.1f} mm',fill=verde)
            C.create_text(205,276,text=f'Topo 41,4 | cota de referência 38,9 | contorno contínuo R5,5',fill=cinza)

        elif kind=='hole':
            C.create_rectangle(75,35,300,220,outline=cinza)
            C.create_oval(108,158,152,202,outline=vermelho,width=2)
            seta_dim(108,145,152,145,'Diâmetro')
            C.create_line(130,180,130,236,fill=azul,arrow='last')
            C.create_line(45,180,130,180,fill=azul,arrow='last')
            C.create_text(220,180,text='Centro X / Y',fill=azul)
            C.create_text(188,258,text='Origem: canto inferior esquerdo',fill=cinza)

        elif kind=='content':
            C.create_rectangle(75,35,300,220,outline=cinza)
            C.create_text(247,78,text='248',font=('Segoe UI',20,'bold'),fill=azul)
            C.create_rectangle(191,127,272,188,outline=verde,width=2)
            C.create_text(231,157,text='QR',font=('Segoe UI',14,'bold'),fill=verde)
            C.create_line(247,78,247,220,fill=azul,dash=(3,2))
            C.create_line(75,78,247,78,fill=azul,dash=(3,2))
            C.create_text(190,254,text='Centro X / Y posiciona o conteúdo',fill=cinza)
        return C
    def ui(self):
        h=ttk.Frame(self,padding=12);h.pack(fill='x');ttk.Label(h,text='Gerador de Chaveiros para Claviculário',style='Title.TLabel').pack(side='left');ttk.Button(h,text='Abrir configuração',command=self.open_cfg).pack(side='right',padx=3);ttk.Button(h,text='Salvar configuração',command=self.save_cfg).pack(side='right',padx=3)
        pan=ttk.Panedwindow(self,orient='horizontal');pan.pack(fill='both',expand=True,padx=12,pady=(0,12));lc=ttk.Frame(pan);R=ttk.Frame(pan,padding=10);pan.add(lc,weight=3);pan.add(R,weight=5)
        cv=tk.Canvas(lc,highlightthickness=0);sb=ttk.Scrollbar(lc,orient='vertical',command=cv.yview);L=ttk.Frame(cv,padding=(2,2,10,12));L.bind('<Configure>',lambda e:cv.configure(scrollregion=cv.bbox('all')));cv.create_window((0,0),window=L,anchor='nw');cv.configure(yscrollcommand=sb.set);cv.pack(side='left',fill='both',expand=True);sb.pack(side='right',fill='y')
        p=ttk.LabelFrame(L,text='1. Chapa',style='Step.TLabelframe',padding=7);p.pack(fill='x',pady=4)
        for i,(a,n) in enumerate([('Largura (mm)','chapa_l'),('Altura (mm)','chapa_a'),('Margem (mm)','margem'),('Espaçamento (mm)','espaco')]):self.field(p,a,n,i)
        p=ttk.LabelFrame(L,text='2. Formato da peça',style='Step.TLabelframe',padding=7);p.pack(fill='x',pady=4);self.diagram(p,'shape',15);ttk.Checkbutton(p,text='Criar abertura lateral',variable=self.var('rasgo','b')).grid(row=0,column=0,columnspan=2,sticky='w',padx=7)
        items=[('Largura total (mm)','peca_l'),('Largura inferior cotada (mm)','largura_base'),('Altura total (mm)','peca_a'),('Trecho vertical esquerdo (mm)','trecho_vertical_esq'),('Raio dos outros três cantos (mm)','raio_ext'),('Raio especial inferior esquerdo (mm)','raio_inf_esq'),('Entrada X na lateral (mm)','entrada_x'),('Centro Y da entrada (mm)','entrada_y'),('Centro X da ponta (mm)','ponta_x'),('Centro Y da ponta (mm)','ponta_y'),('Largura da abertura (mm)','largura_rasgo'),('Raio superior da boca (mm)','raio_boca_sup'),('Raio inferior da boca (mm)','raio_boca_inf'),('Raio da ponta interna (mm)','raio_ponta')]
        for i,(a,n) in enumerate(items,1):self.field(p,a,n,i)
        p=ttk.LabelFrame(L,text='3. Furo da argola',style='Step.TLabelframe',padding=7);p.pack(fill='x',pady=4);self.diagram(p,'hole',5);ttk.Checkbutton(p,text='Criar furo',variable=self.var('furo','b')).grid(row=0,column=0,columnspan=2,sticky='w',padx=7)
        for i,(a,n) in enumerate([('Diâmetro (mm)','furo_d'),('Centro X (mm)','furo_x'),('Centro Y (mm)','furo_y')],1):self.field(p,a,n,i)
        p=ttk.LabelFrame(L,text='4. Conteúdo',style='Step.TLabelframe',padding=7);p.pack(fill='x',pady=4);self.diagram(p,'content',16);ttk.Checkbutton(p,text='Adicionar texto / numeração',variable=self.var('texto','b')).grid(row=0,column=0,columnspan=2,sticky='w',padx=7)
        for i,(a,n) in enumerate([('Número inicial','inicial'),('Número final','final'),('Dígitos','digitos'),('Prefixo','prefixo'),('Sufixo','sufixo')],1):self.field(p,a,n,i)
        ttk.Label(p,text='Fonte').grid(row=6,column=0,sticky='w',padx=7);ttk.Combobox(p,textvariable=self.var('fonte'),values=sorted(set(f.name for f in fontManager.ttflist)),state='readonly',width=23).grid(row=6,column=1,padx=7)
        for i,(a,n) in enumerate([('Altura do texto (mm)','texto_h'),('Centro X do texto (mm)','texto_x'),('Centro Y do texto (mm)','texto_y')],7):self.field(p,a,n,i)
        ttk.Checkbutton(p,text='Adicionar QR Code',variable=self.var('qr','b')).grid(row=10,column=0,columnspan=2,sticky='w',padx=7,pady=(8,0))
        for i,(a,n) in enumerate([('Conteúdo ou link','qr_texto'),('Tamanho (mm)','qr_tamanho'),('Centro X do QR (mm)','qr_x'),('Centro Y do QR (mm)','qr_y')],11):self.field(p,a,n,i)
        ttk.Label(R,text='Pré-visualização e conferência',font=('Segoe UI',13,'bold')).pack(anchor='w');ttk.Label(R,text='Vermelho: corte | Azul: gravação',foreground='#555').pack(anchor='w');self.prev=ttk.Label(R,anchor='center',relief='solid');self.prev.pack(fill='both',expand=True,pady=7);self.status=ttk.Label(R);self.status.pack(anchor='w')
        formats=ttk.LabelFrame(R,text='Formatos que serão salvos',padding=8);formats.pack(fill='x',pady=6);ttk.Checkbutton(formats,text='DXF para fabricação',variable=self.var('saida_dxf','b')).pack(side='left',padx=8);ttk.Checkbutton(formats,text='PNG para visualização',variable=self.var('saida_png','b')).pack(side='left',padx=8);ttk.Checkbutton(formats,text='PDF para conferência',variable=self.var('saida_pdf','b')).pack(side='left',padx=8)
        b=ttk.Frame(R);b.pack(fill='x',pady=4);b.columnconfigure(0,weight=1,uniform='acoes');b.columnconfigure(1,weight=1,uniform='acoes');ttk.Button(b,text='VISUALIZAR E VERIFICAR',style='Primary.TButton',command=self.verify).grid(row=0,column=0,sticky='ew',padx=(0,4));ttk.Button(b,text='SALVAR ARQUIVOS...',style='Primary.TButton',command=self.save_files).grid(row=0,column=1,sticky='ew',padx=(4,0))
    def load(self):
        """Copia as configuracoes atuais para os campos da janela."""
        for n,v in self.v.items():v.set(getattr(self.c,n));self.changed=False
    def read(self):
        """Le os campos, converte tipos, valida e calcula as chapas."""
        c=Cfg();floats={'chapa_l','chapa_a','margem','espaco','peca_l','largura_base','peca_a','trecho_vertical_esq','raio_ext','raio_inf_esq','entrada_x','entrada_y','ponta_x','ponta_y','largura_rasgo','raio_boca_sup','raio_boca_inf','raio_ponta','furo_d','furo_x','furo_y','texto_h','texto_x','texto_y','qr_tamanho','qr_x','qr_y'};ints={'inicial','final','digitos','dpi'};bools={'rasgo','furo','texto','qr','saida_dxf','saida_png','saida_pdf'}
        for n,v in self.v.items():setattr(c,n,fnum(v.get(),n) if n in floats else fint(v.get(),n) if n in ints else bool(v.get()) if n in bools else str(v.get()))
        self.c=ajustar(c);e=validar(c)
        if e:raise ValueError('\n'.join('• '+x for x in e))
        return c,make_layouts(c)
    def preview(self):
        """Atualiza a imagem de conferencia exibida na direita."""
        try:
            c,L=self.read();p=Path(tempfile.gettempdir())/'clav_v5.png';render(c,L[0],p,75);im=Image.open(p);im.thumbnail((max(550,self.prev.winfo_width()-15),max(400,self.prev.winfo_height()-15)));self.photo=ImageTk.PhotoImage(im);self.prev.configure(image=self.photo);self.status.configure(text=f'{c.final-c.inicial+1} peças | {len(L)} chapas | {len(L[0])} peças na primeira chapa')
        except Exception as e:messagebox.showerror('Revise as informações',str(e))
    def verify(self):
        try:self.preview();c,L=self.read();messagebox.showinfo('Projeto verificado',f'Configuração válida.\n\n{c.final-c.inicial+1} peças em {len(L)} chapa(s).\nFaça uma peça de teste antes do lote.')
        except Exception as e:messagebox.showerror('Revise as informações',str(e))
    def save_files(self):
        """Solicita um destino e salva os formatos escolhidos."""
        try:c,L=self.read()
        except Exception as e:messagebox.showerror('Revise as informações',str(e));return
        path=filedialog.asksaveasfilename(title='Escolha o nome e o local dos arquivos',initialfile=safe(c.nome)+'.dxf',defaultextension='.dxf',filetypes=[('Arquivo DXF','*.dxf'),('Todos os arquivos','*.*')])
        if not path:return
        try:
            A=[]
            if c.saida_dxf:A+=export_dxf(c,L,path)
            A+=export_other(c,L,path)
            messagebox.showinfo('Arquivos salvos',f'{len(A)} arquivo(s) salvo(s) em:\n\n{Path(path).parent}')
        except Exception as e:messagebox.showerror('Falha ao salvar',str(e))
    def save_cfg(self):
        """Salva os campos atuais em um arquivo .projetolaser."""
        try:c,L=self.read()
        except Exception as e:messagebox.showerror('Revise as informações',str(e));return
        p=filedialog.asksaveasfilename(defaultextension='.projetolaser',filetypes=[('Projeto Laser','*.projetolaser')]);
        if p:Path(p).write_text(json.dumps(asdict(c),ensure_ascii=False,indent=2),encoding='utf-8')
    def open_cfg(self):
        """Abre um projeto salvo anteriormente e atualiza a tela."""
        p=filedialog.askopenfilename(filetypes=[('Projeto Laser','*.projetolaser')]);
        if not p:return
        try:self.c=Cfg(**json.loads(Path(p).read_text(encoding='utf-8')));self.load();self.preview()
        except Exception as e:messagebox.showerror('Arquivo inválido',str(e))

# -----------------------------------------------------------------------------
# 9. INICIO DO PROGRAMA
# -----------------------------------------------------------------------------
# Este bloco so e executado quando main_comentado.py e aberto diretamente.
if __name__=='__main__':
    App().mainloop()

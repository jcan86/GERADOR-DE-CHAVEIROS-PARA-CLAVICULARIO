# Gerador de Chaveiros para Claviculário

Aplicativo desenvolvido para criar, visualizar, conferir e exportar arquivos de fabricação de chaveiros numerados para claviculários. O programa gera arquivos DXF compatíveis com softwares de desenho técnico e equipamentos de corte a laser, além de permitir a geração opcional de imagens PNG e documentos PDF para conferência.

## Desenvolvedor

**Jesus Cavalcante de Assis Neto**

## Finalidade do programa

O programa automatiza a criação de conjuntos de chaveiros numerados, reduzindo o trabalho manual de desenhar cada peça, posicionar números, organizar peças na chapa e preparar os arquivos para fabricação.

A geometria principal foi baseada em um modelo mestre desenhado e conferido no AutoCAD. O contorno exportado preserva as coordenadas e os arcos definidos no modelo de referência.

## Principais recursos

- Geração automática de chaveiros numerados.
- Definição do número inicial e do número final.
- Controle da quantidade de dígitos da numeração.
- Inclusão opcional de prefixo e sufixo.
- Seleção da fonte utilizada na gravação.
- Configuração da altura e da posição do texto.
- Inclusão opcional de QR Code.
- Configuração do tamanho e da posição do QR Code.
- Definição das dimensões da chapa.
- Configuração de margem e espaçamento entre peças.
- Distribuição automática das peças na chapa.
- Pré-visualização do projeto antes da fabricação.
- Verificação das medidas e da quantidade de chapas.
- Exportação em DXF para fabricação.
- Exportação opcional em PNG para visualização.
- Exportação opcional em PDF para conferência.
- Escolha do nome e do local de salvamento dos arquivos.
- Salvamento e abertura das configurações do projeto.

## Geometria do modelo mestre

O modelo padrão utiliza as seguintes referências:

- Largura total: **41,4 mm**.
- Altura total: **38,1 mm**.
- Abertura diagonal na lateral esquerda.
- Ponta interna arredondada.
- Raio especial no canto inferior esquerdo.
- Furo para instalação da argola.
- Lado direito vertical.

O arquivo DXF utiliza o contorno mestre extraído do desenho final elaborado no AutoCAD. A pré-visualização utiliza o mesmo contorno, convertido em pontos somente para exibição na tela.

## Organização da interface

A interface foi organizada em quatro áreas principais:

### 1. Chapa

Permite configurar:

- largura da chapa;
- altura da chapa;
- margem externa;
- espaçamento entre as peças.

### 2. Formato da peça

Apresenta as dimensões e referências geométricas do chaveiro. A representação técnica ajuda a relacionar cada campo com a região correspondente da peça.

### 3. Furo da argola

Permite configurar:

- diâmetro do furo;
- posição horizontal do centro;
- posição vertical do centro.

A origem das coordenadas é considerada no canto inferior esquerdo da peça.

### 4. Conteúdo

Permite configurar:

- numeração inicial e final;
- quantidade de dígitos;
- prefixo e sufixo;
- fonte;
- altura e posição do texto;
- conteúdo, tamanho e posição do QR Code.

## Botões principais

### Visualizar e verificar

Atualiza a pré-visualização e verifica se as informações preenchidas são válidas. O programa também informa a quantidade total de peças, a quantidade de chapas e o número de peças posicionadas na primeira chapa.

### Salvar arquivos

Abre a janela de salvamento do Windows para que o usuário escolha o nome e o local dos arquivos. Os formatos marcados na interface são gerados no local selecionado.

Quando o projeto exige mais de uma chapa, o programa acrescenta automaticamente uma identificação ao nome dos arquivos:

```text
nome_chapa_001.dxf
nome_chapa_002.dxf
nome_chapa_003.dxf
```

## Como executar o código-fonte

Abra o terminal na pasta do programa e execute:

```powershell
.\.venv\Scripts\python.exe .\main.py
```

Não é necessário ativar o ambiente virtual pelo arquivo `Activate.ps1`.

## Instalação das dependências

Na primeira execução, utilize:

```powershell
py -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r .\requirements.txt; .\.venv\Scripts\python.exe .\main.py
```

## Compilação do executável

Para gerar um executável único para Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pyinstaller; .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name "Gerador_Claviculario" --collect-all matplotlib --collect-all qrcode --collect-all reportlab --collect-all ezdxf .\main.py
```

O executável será criado em:

```text
dist\Gerador_Claviculario.exe
```

## Arquivos importantes

```text
main.py
```

Código-fonte principal do programa.

```text
requirements.txt
```

Lista das bibliotecas necessárias.

```text
*.projetolaser
```

Arquivos de configuração salvos pelo usuário.

```text
dist\Gerador_Claviculario.exe
```

Executável compilado para Windows.

## Edição do código

O código-fonte pode ser editado em qualquer editor compatível com Python, como o Visual Studio Code.

Antes de alterar a geometria, faça uma cópia de segurança do arquivo `main.py`. As principais partes do código devem permanecer separadas e comentadas:

1. configurações padrão;
2. validação de valores;
3. geometria do contorno;
4. distribuição das peças na chapa;
5. geração do texto e do QR Code;
6. exportação DXF, PNG e PDF;
7. construção da interface;
8. salvamento e abertura das configurações.

## Cuidados antes da fabricação

- Gere inicialmente apenas uma peça de teste.
- Confira se o arquivo está em milímetros.
- Verifique a escala 1:1 no software da máquina.
- Confirme se o contorno está fechado.
- Confira as camadas de corte e gravação.
- Verifique a posição do texto e do furo.
- Somente após a conferência, gere e corte o lote completo.

## Licença e utilização

Este programa foi desenvolvido para apoiar a criação e a fabricação de chaveiros para claviculários. Qualquer alteração, distribuição ou reutilização deve preservar a identificação do desenvolvedor no código-fonte e na documentação.

---

**Desenvolvido por Jesus Cavalcante de Assis Neto**

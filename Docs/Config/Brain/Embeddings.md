# Guia de Aceleração por Hardware para Embeddings

O motor vetorial utiliza internamente o **ONNX Runtime** via biblioteca `fastembed` para gerar os embeddings do modelo `all-MiniLM-L6-v2`. Por padrão, se o hardware não for detectado ou faltarem drivers no container, o sistema aplica fallback para a CPU (`CPUExecutionProvider`).

Abaixo estão os passos para habilitar a aceleração de hardware nativa de acordo com cada tipo de GPU/iGPU.

## 1. NVIDIA (RTX e GTX) — `CUDAExecutionProvider`

Placas dedicadas da NVIDIA oferecem o maior ganho de taxa de inferência quando configuradas via CUDA e cuDNN.

### A. Dependências no Host

- **Driver NVIDIA:** Certifique-se de que os drivers proprietários da placa estão instalados (`nvidia-smi` funcionando).
- **CUDA Toolkit & cuDNN:** Recomendado CUDA 11.8 ou 12.x e cuDNN compatível instalado no sistema ou no container.

### B. Instalação de Pacotes Python

Substitua o `onnxruntime` padrão pela versão com suporte a CUDA:

```bash
pip uninstall onnxruntime -y
pip install onnxruntime-gpu
```

### C. Configuração no Docker

Caso o bot rode em container Docker, é obrigatório repassar a GPU ao container:

1. Instale o **NVIDIA Container Toolkit** no sistema hospedeiro.
2. Adicione a flag de GPU na execução do container:

```bash
docker run --gpus all -d sambot-image
```

Ou no `docker-compose.yml`:

```yaml
services:
  sambot:
    # ...
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

## 2. Placas AMD (Radeon RX) e iGPUs em Windows — `DmlExecutionProvider` (DirectML)

O **DirectML** é uma API de baixo nível desenvolvida pela Microsoft compatível com DirectX 12. É a melhor opção para placas **AMD Radeon (série RX)**, **Intel Arc**, iGPUs integradas da Intel/AMD e GPUs NVIDIA em ambientes Windows/WSL2.

### A. Requisitos

- Sistema Windows 10/11 ou WSL2 com suporte a DirectX 12.
- Drivers de vídeo da fabricante atualizados.

### B. Instalação de Pacotes Python

Instale o backend DirectML do ONNX:

```bash
pip uninstall onnxruntime onnxruntime-gpu -y
pip install onnxruntime-directml
```

### C. Comportamento

O provedor `DmlExecutionProvider` será automaticamente acionado pela lista prioritária sem a necessidade de instalar pacotes de desenvolvimento proprietários como ROCm ou CUDA.

## 3. Placas AMD Radeon (RX) em Linux Nativo — `ROCmExecutionProvider`

Em distribuições Linux puras sem DirectML, placas AMD dedicadas utilizam a plataforma ROCm.

### A. Requisitos

- Placa AMD suportada (arquiteturas RDNA 2, RDNA 3 ou instâncias específicas).
- Drivers ROCm instalados no Linux (`rocminfo` operacional).

### B. Instalação de Pacotes Python

Instale a build do ONNX Runtime compilada para ROCm (disponibilizada nos canais oficiais da AMD/ROCm):

```bash
pip install onnxruntime-rocm

```

## 4. Intel (CPUs modernas, iGPUs UHD/Iris Xe e GPUs Intel Arc) — `OpenVINOExecutionProvider`

O **OpenVINO** otimiza redes neurais para extrair desempenho de processadores Intel, gráficos integrados e NPUs.

### A. Requisitos

- Processador Intel (Core de 6ª geração ou superior), iGPU Intel Iris Xe/UHD ou placa dedicada Intel Arc.
- Drivers OpenVINO/Compute Runtime instalados.

### B. Instalação de Pacotes Python

Instale a extensão OpenVINO para o ONNX Runtime:

```bash
pip install onnxruntime-openvino

```

## 5. Fallback (CPU Pura) — `CPUExecutionProvider`

Caso o container esteja em execução em servidores virtuais (VPS), máquinas sem GPU dedicada ou ambientes com restrição de tamanho de imagem Docker:

- Não requer bibliotecas adicionais além do `fastembed` básico.
- Consumo mínimo de memória em disco.
- Para modelos ultra-leves como o `all-MiniLM-L6-v2` (~22M de parâmetros), o tempo de inferência por requisição varia em torno de **8 a 15 ms**, tornando o uso de CPU suficiente para a maior parte das cargas operacionais.

## 6. Alternativas de Modelos de Embeddings (Propósitos e Dimensões)

O `fastembed` suporta nativamente diversos modelos pré-quantizados no formato ONNX. Para trocar de modelo, basta alterar o parâmetro `model_name` no construtor do `SmartEmbeddingFunction`.

> **Atenção:** Ao trocar de modelo, se o tamanho do vetor (dimensões) mudar, recrie ou limpe a coleção no ChromaDB (`Data/Persistence/VectorDB`), pois vetores com tamanhos conflitantes na mesma coleção geram erro de inserção.

### Tabela Comparativa

| Modelo                                                        | Dimensões |        Idioma Foco        | Tamanho (~Disk) | Propósito Recomendado                                                                                                                                            |
| :------------------------------------------------------------ | :-------: | :-----------------------: | :-------------: | :--------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sentence-transformers/all-MiniLM-L6-v2` _(Padrão)_           |  **384**  |      Inglês / Geral       |     ~90 MB      | **Uso geral ultra-leve.** Baixíssimo consumo de CPU e ideal para comandos rápidos de roteamento (`TLMRouter`).                                                   |
| `BAAI/bge-small-en-v1.5`                                      |  **384**  |          Inglês           |     ~130 MB     | **Busca semântica balanceada.** Excelente taxa de precisão (MTEB) para seu peso.                                                                                 |
| `BAAI/bge-base-en-v1.5`                                       |  **768**  |          Inglês           |     ~430 MB     | **RAG denso.** Ideal quando há documentos longos e o contexto semântico exige mais precisão conceitual.                                                          |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |  **384**  | Multilíngue (50+ idiomas) |     ~470 MB     | **Melhor custo-benefício para Português.** Compreende gírias, frases em PT-BR e variações lexicais com mais estabilidade que o modelo apenas em inglês.          |
| `intfloat/multilingual-e5-small`                              |  **384**  |        Multilíngue        |     ~450 MB     | **Classificação e busca multilíngue.** Exige prefixar buscas com `"query: "` e passagens com `"passage: "`, mas entrega alta precisão em sentenças em português. |
| `nomic-ai/nomic-embed-text-v1.5`                              |  **768**  |    Multilíngue / Longo    |     ~550 MB     | **Contexto estendido.** Suporta janelas de contexto de até 8192 tokens (contra 512 dos modelos MiniLM convencionais).                                            |

---

### Como trocar de modelo no código:

No arquivo `Brain/Memory/LongTerm/_embeddings.py`:

```python
# Exemplo 1: Otimizado para português
self.model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Exemplo 2: Precisão superior para RAG complexo
self.model_name = "BAAI/bge-base-en-v1.5"
```

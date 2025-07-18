FROM continuumio/miniconda3

COPY environment.yml /tmp/environment.yml
RUN conda env remove -n py-xiaozhi || true
RUN conda env create -f /tmp/environment.yml

# 將 conda 環境加入 PATH
ENV PATH /opt/conda/envs/py-xiaozhi/bin:$PATH

WORKDIR /app
COPY . /app

# 安裝 pip 套件
RUN /opt/conda/envs/py-xiaozhi/bin/pip install -r requirements.txt

CMD ["conda", "run", "--no-capture-output", "-n", "py-xiaozhi", "python", "main.py"]

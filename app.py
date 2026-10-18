# app.py
from flask import Flask, render_template, request, jsonify
from nlp_pipeline import answer  # 统一问答流水线（意图→NER→规范化→Cypher→Neo4j）

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')  # 渲染前端页面


@app.route('/ask', methods=['POST'])
def ask():
    # 获取用户输入的问题
    question = request.form['question']

    # 调用问答流水线，返回答案列表（模型不可用时自动回退词典版）
    result = answer(question)

    # 将结果封装成 JSON 返回给前端
    return jsonify(answer=result)


if __name__ == '__main__':
    app.run(debug=True)

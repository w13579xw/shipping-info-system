from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import json
from openai import OpenAI
import traceback
from app01.utils.build_kg_utils import PortKnowledgeGraphBuilder
from myProject.settings import OPENAI_API_KEY, OPENAI_BASE_URL

def qa_page(request):
    # 记录模块访问
    from app01.models import ModuleVisit, UserInfo
    user = None
    if request.session.get('user_info'):
        user = UserInfo.objects.get(id=request.session['user_info']['id'])
    ModuleVisit.objects.create(module_name='knowledge_graph', user=user)
    return render(request, 'qa.html')

@csrf_exempt
def ask_question(request):
    if request.method != 'POST':
        return JsonResponse({
            'code': 405,
            'message': '仅支持POST请求',
            'data': None
        }, status=405)
    
    try:
        data = json.loads(request.body)
        question = data.get('question')
        
        if not question:
            return JsonResponse({
                'code': 400,
                'message': '问题不能为空',
                'data': None
            }, status=400)
        
        
        # 初始化OpenAI客户端
        try:
            client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        except Exception as e:
            print(f"OpenAI客户端初始化错误：{str(e)}")
            error_traceback = traceback.format_exc()
            print(f"错误详情：{error_traceback}")
            return JsonResponse({
                'code': 500,
                'message': '服务初始化失败，请稍后重试',
                'data': None
            }, status=500)
        
        # 先让AI分析问题是否涉及知识图谱中的实体和关系
        try:
            analysis_response = client.chat.completions.create(
                model="deepseek-chat",
                timeout=60,  # 设置60秒超时
                messages=[
                    {"role": "system", "content": "你是一个专业的问题分析助手，负责将用户问题转换为Neo4j的Cypher查询语句。\n\n可用的实体和关系：\n实体（每个实体只有name属性）：\n- 港口 (name)\n- 城市 (name)\n- 国家 (name)\n- 地区 (name)\n- 航线 (name)\n\n关系：\n- [:belongs_to] - 城市属于国家\n- [:located_in] - 港口位于城市\n- [:in_region] - 港口位于地区\n- [:on_route] - 港口在航线上\n\n你的任务是：\n1. 分析用户问题是否涉及上述实体和关系\n2. 如果涉及且只使用已定义的属性，返回对应的Cypher查询语句，必须以'MATCH'开头\n3. 如果涉及未定义的属性或不涉及上述实体和关系，返回'NO'\n\n注意事项：\n1. 只返回查询语句或'NO'，不要包含任何解释或描述\n2. 查询语句必须使用正确的节点标签和关系类型\n3. 只能使用已定义的属性(name)进行查询\n4. 如果问题涉及实体的其他属性(如大小、容量等)，返回'NO'\n\n示例问题和答案：\n问：上海有哪些港口？\n答：MATCH (p:港口)-[:located_in]->(c:城市) WHERE c.name = '上海' RETURN p.name\n\n问：中国的港口有哪些？\n答：MATCH (p:港口)-[:located_in]->(c:城市)-[:belongs_to]->(co:国家) WHERE co.name = '中国' RETURN p.name\n\n问：这艘船什么时候到港？\n答：NO\n\n问：上海港的吞吐量是多少？\n答：NO"},
                    {"role": "user", "content": question}
                ],
                stream=False
            )
            
            if not analysis_response or not hasattr(analysis_response, 'choices') or not analysis_response.choices:
                raise ValueError('API返回数据格式异常')
            
            analysis_result = analysis_response.choices[0].message.content
            
            # 如果分析结果包含Cypher查询语句，则查询知识图谱
            # 验证分析结果格式
            analysis_result = analysis_result.strip()
            if analysis_result != 'NO' and analysis_result.upper().startswith('MATCH'):
                try:
                    # 初始化知识图谱查询器
                    kg = PortKnowledgeGraphBuilder()
                    # 输出Cypher查询语句
                    print(f"执行的Cypher查询语句: {analysis_result}")
                    # 执行Cypher查询
                    # 执行Cypher查询并对结果进行去重处理
                    result = list({str(r): r for r in kg.graph.run(analysis_result).data()}.values())
                    # 输出查询结果
                    print(f"查询结果: {result}")
                    
                    if result:
                        # 统计查询结果数量
                        result_count = len(result)
                        # 让AI生成基于查询结果的自然语言回答
                        answer_response = client.chat.completions.create(
                            model="deepseek-chat",
                            timeout=60,  # 设置60秒超时
                            messages=[
                                {"role": "system", "content": "你是一个专业的航运领域问答助手。请根据知识图谱的查询结果，生成自然、专业的回答。在回答中，请确保完整展示所有查询结果，并在开头说明找到了多少个结果。"},
                                {"role": "user", "content": f"问题：{question}\n查询结果：{result}\n结果数量：{result_count}"}
                            ],
                            stream=False
                        )
                        answer = "📚 根据知识图谱查询结果：\n\n" + answer_response.choices[0].message.content
                    else:
                        # 如果知识图谱中没有找到信息，添加提示并使用AI模型回答
                        answer_response = client.chat.completions.create(
                            model="deepseek-chat",
                            timeout=60,  # 设置60秒超时
                            messages=[
                                {"role": "system", "content": "你是一个专业的航运领域问答助手。你拥有丰富的航运知识，包括船舶类型、航运规则、港口运营、海事法规等。请以专业、准确且友好的方式回答用户的问题。"},
                                {"role": "user", "content": question}
                            ],
                            stream=False
                        )
                        answer = "🤖 AI助手回答：\n\n" + answer_response.choices[0].message.content
                except Exception as e:
                    print(f"知识图谱查询错误，回退为直接问答：{str(e)}")
                    # Neo4j 不可用时，回退为直接使用大模型回答
                    try:
                        answer_response = client.chat.completions.create(
                            model="deepseek-chat",
                            timeout=60,
                            messages=[
                                {"role": "system", "content": "你是一个专业的航运领域问答助手。你拥有丰富的航运知识，包括船舶类型、航运规则、港口运营、海事法规等。请以专业、准确且友好的方式回答用户的问题。"},
                                {"role": "user", "content": question}
                            ],
                            stream=False
                        )
                        answer = "🤖 AI助手回答：\n\n" + answer_response.choices[0].message.content
                    except Exception as e2:
                        answer = "抱歉，问答服务暂不可用，请稍后重试。"
            else:
                # 如果不涉及知识图谱中的实体和关系，则直接使用AI回答
                answer_response = client.chat.completions.create(
                    model="deepseek-chat",
                    timeout=60,  # 设置60秒超时
                    messages=[
                        {"role": "system", "content": "你是一个专业的航运领域问答助手。你拥有丰富的航运知识，包括船舶类型、航运规则、港口运营、海事法规等。请以专业、准确且友好的方式回答用户的问题。"},
                        {"role": "user", "content": question}
                    ],
                    stream=False
                )
                answer = "🤖 AI助手回答：\n\n" + answer_response.choices[0].message.content
            
            return JsonResponse({
                'code': 200,
                'message': '成功',
                'data': {
                    'answer': answer
                }
            }, status=200)
            
        except Exception as e:
            print(f"API调用错误：{str(e)}")
            error_traceback = traceback.format_exc()
            print(f"错误详情：{error_traceback}")
            return JsonResponse({
                'code': 500,
                'message': '服务调用失败，请稍后重试',
                'data': None
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '无效的JSON数据',
            'data': None
        }, status=400)
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"服务器内部错误：{str(e)}")
        print(f"错误详情：{error_traceback}")
        return JsonResponse({
            'code': 500,
            'message': f'服务器内部错误：{str(e)}',
            'data': None
        }, status=500)
                
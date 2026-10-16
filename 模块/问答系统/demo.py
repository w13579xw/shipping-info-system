#!/usr/bin/env python
# -*- coding:utf-8 -*-

# from openai import OpenAI
#
# client = OpenAI(api_key="your-api-key-here", base_url="https://api.deepseek.com")
#
# response = client.chat.completions.create(
#
# model="deepseek-chat",
#
# messages=[
#
# {"role": "system", "content": "You are a helpful assistant"},
#
# {"role": "user", "content": "who r u？"},
#
# ],
#
# stream=False
#
# )
#
# print(response.choices[0].message.content)

from openai import OpenAI

def main():
    client = OpenAI(api_key="your-api-key-here", base_url="https://api.deepseek.com")

    print("欢迎使用连续提问程序！输入'退出'或'结束'来结束程序。")
    while True:
        user_input = input("请输入您的问题或指令: ")
        if user_input.lower() in ['退出', '结束']:
            print("感谢使用，再见！")
            break
        else:
            response = client.chat.completions.create(
                model="deepseek-reasoner",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": user_input},
                ],
                stream=False
            )
            print(response.choices[0].message.content)

if __name__ == "__main__":
    main()

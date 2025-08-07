from langchain_community.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

# -------------------------
# 1. 설정 - GPT 키 및 모델
# -------------------------
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(temperature=0.7, model_name="gpt-3.5-turbo")

# -------------------------
# 2. LangChain Memory & 프롬프트 구성
# -------------------------
memory = ConversationBufferMemory(return_messages=True)

template = """
당신은 여행사 고객센터 직원입니다. 고객의 질문에 친절하고 간결하게 답하세요.

대화 이력:
{history}

고객 질문:
{input}

답변:
"""
prompt = PromptTemplate(
    input_variables=["history", "input"],
    template=template
)

conversation = ConversationChain(
    llm=llm,
    prompt=prompt,
    memory=memory,
    verbose=False
)

# -------------------------
# 3. Streamlit UI
# -------------------------
st.title("✈️ LangChain 기반 여행 고객센터 AI")
st.write("LangChain + GPT로 구현한 스마트 고객 응대 에이전트입니다.")

user_input = st.text_input("고객 질문을 입력해주세요:", "수하물 규정 알려주세요")

if st.button("답변 받기"):
    response = conversation.predict(input=user_input)
    st.success(response)

    # 로그 저장
    log = pd.DataFrame({"질문": [user_input], "답변": [response]})
    if os.path.exists("log_langchain.csv"):
        log.to_csv("log_langchain.csv", mode='a', index=False, header=False)
    else:
        log.to_csv("log_langchain.csv", index=False)

# -------------------------
# 4. 실행 전 준비사항
# -------------------------
# 1. 환경 변수에 OPENAI_API_KEY 설정 또는 `.env`로 불러오기
# 2. pip install langchain openai streamlit pandas
# 3. streamlit run [이 파일명].py
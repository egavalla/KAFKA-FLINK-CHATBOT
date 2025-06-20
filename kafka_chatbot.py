import requests
import time
import streamlit as st
import json
import traceback
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Explicitly inject credentials into os.environ
os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID", "")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY", "")
os.environ["AWS_SESSION_TOKEN"] = os.getenv("AWS_SESSION_TOKEN", "")
os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_DEFAULT_REGION", "us-west-2")

if "authentication_status" not in st.session_state:
    st.session_state.authentication_status = False
if "llm" not in st.session_state:
    st.session_state.llm = None

def changeModel():
    """Initialize the Bedrock client using direct credentials from .env (temporary credentials support)"""
    try:
        bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=os.environ["AWS_DEFAULT_REGION"],
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            aws_session_token=os.environ["AWS_SESSION_TOKEN"]
        )
        st.session_state.llm = bedrock_client
        st.session_state.authentication_status = True
        st.sidebar.success("You have successfully authenticated with AWS Bedrock", icon='✅')
    except (BotoCoreError, ClientError) as e:
        st.sidebar.error(f"Authentication failed: {str(e)}", icon='❌')

def call_bedrock(messages):
    try:
        if not st.session_state.llm:
            raise RuntimeError("Bedrock client not initialized.")

        prompt = "\n\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in messages])
        prompt = f"\n\nHuman: {prompt}\n\nAssistant:"

        response = st.session_state.llm.invoke_model(
            modelId="anthropic.claude-v2",
            body=json.dumps({
                "prompt": prompt,
                "max_tokens_to_sample": 1000,
                "temperature": 0.2,
                "top_k": 250,
                "top_p": 1,
                "stop_sequences": ["\n\nHuman:"]
            }),
            contentType="application/json"
        )
        response_body = json.loads(response['body'].read())
        return response_body['completion'].strip()
    except Exception as e:
        st.error(f"Error calling Bedrock: {str(e)}")
        return "select * from customer_accounts limit 10"

# Sidebar configuration
with st.sidebar:
    with st.form("llm_form"):
        st.title('LLM Configuration')
        confluentCloudProvider = st.selectbox("LLM provider", ["bedrock-claude-v2"], key="llmProvider")
        st.write("(No key required for AWS Bedrock if IAM or .env credentials are configured)")
        submit_llm_button = st.form_submit_button("Submit", on_click=changeModel)

    with st.form("flink_form"):
        st.title('Confluent Configuration')
        confluentApiKey = st.text_input("Confluent Flink API Key", key="confluentApiKey", value=os.getenv("CONFLUENT_API_KEY", ""))
        confluentApiSecret = st.text_input("Confluent Flink API Secret", type="password", key="confluentApiSecret", value=os.getenv("CONFLUENT_API_SECRET", ""))
        confluentEnvironment = st.text_input("Confluent Environment ID", key="confluentEnvironment", value=os.getenv("CONFLUENT_ENVIRONMENT_ID", ""))
        confluentOrg = st.text_input("Confluent Organization ID", key="confluentOrg", value=os.getenv("CONFLUENT_ORG_ID", ""))
        confluentPool = st.text_input("Confluent Flink Compute Pool", key="confluentPool", value=os.getenv("CONFLUENT_POOL_ID", ""))
        confluentPrincipal = st.text_input("Confluent Flink Principal", key="confluentPrincipal", value=os.getenv("CONFLUENT_PRINCIPAL", ""))
        confluentCatalog = st.text_input("Confluent Flink Environment Name", key="confluentCatalog", value=os.getenv("CONFLUENT_CATALOG", ""))
        confluentDatabase = st.text_input("Confluent Kafka Cluster Name(Flink DB)", key="confluentDatabase", value=os.getenv("CONFLUENT_DATABASE", ""))
        azure_index = ["azure", "aws", "gcp"].index("aws")
        confluentCloudProvider = st.selectbox("Cloud provider", ["azure", "aws", "gcp"], key="confluentCloudProvider", index=azure_index)
        confluentCloudRegion = st.text_input("Cloud provider region", key="confluentCloudRegion", value=os.getenv("CONFLUENT_CLOUD_REGION", "us-west-2"))
        submit_button = st.form_submit_button("Submit", on_click=lambda: st.session_state.update({"schema": None, "submitted": True}))

    if st.button("List Bedrock Models"):
        try:
            client = boto3.client(
                "bedrock",
                region_name=os.environ["AWS_DEFAULT_REGION"],
                aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
                aws_session_token=os.environ["AWS_SESSION_TOKEN"]
            )
            models = client.list_foundation_models()
            st.json(models)
        except Exception as e:
            st.error(f"Model listing failed: {str(e)}")

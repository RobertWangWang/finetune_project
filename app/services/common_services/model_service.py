import json
from typing import List

from openai import OpenAI, APIError, APIConnectionError, RateLimitError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.common_db_model import model_db
from app.db.common_db_model.model_db import ProviderModelORM, ProviderORM, get_provider_model
from app.lib.i18n.config import i18n
from app.models.common_models.llm_model import LLMModel, LLMModelList, LLMItem, LLMSaveRequest
from app.models.user_model import User


def orm_to_provider_model(orm: ProviderModelORM) -> LLMItem:
    llm = LLMItem(
        id=orm.id,
        name=orm.account_name,
        model_name=orm.model_name,
        model_type=orm.model_type,
        capability=orm.capability,
        is_valid=orm.is_valid,
        is_default=orm.is_default,

        api_key=orm.config.get("apiKey"),
        endpoint_id=orm.config.get("endpointId")
    )
    return llm


def model_to_orm(save: LLMSaveRequest) -> (ProviderORM, ProviderModelORM):
    provider = ProviderORM(
        provider_name="open_ai",
        account_name=save.name,
        is_valid=True,
        access_config={}
    )

    model = ProviderModelORM(
        provider_name="open_ai",
        model_name=save.model_name,
        model_type=save.model_type,
        config={
            "apiKey": save.api_key,
            "endpointId": save.endpoint_id
        },
        is_valid=True,
        is_default=False,
        account_name=save.name,
        # provider_id=provider_orm.id,
        capability=save.capability
    )
    return provider, model


def list_model(session: Session, current_user: User, page_no: int, page_size: int) -> LLMModelList:
    model_list_orm, total = model_db.list_model(session, current_user, page_no, page_size)
    # provide_id_list = []
    # for model_orm in model_list_orm:
    #     provide_id_list.append(model_orm.id)
    # provider_list, _ = model_db.list_provider(session, current_user, page_no, len(provide_id_list), ids=provide_id_list)
    # provider_map = {provider.id: provider for provider in provider_list}

    model_list: List[LLMItem] = []
    for model_orm in model_list_orm:
        item = orm_to_provider_model(model_orm)
        model_list.append(item)
    return LLMModelList(items=model_list, total=total)


def create_model(session: Session, current_user: User, create: LLMSaveRequest) -> LLMItem:
    provider, model = model_to_orm(create)
    provider_orm = model_db.create_provider(session, current_user, provider)

    model.provider_id = provider_orm.id
    model_orm = model_db.create_model(session, current_user, model)
    return orm_to_provider_model(model_orm)


def update_model(session: Session, current_user: User, id: str, update: LLMSaveRequest) -> LLMItem:
    provider_model_orm = model_db.get_model(session, current_user, id)
    provider_orm = model_db.get_provider(session, current_user, provider_model_orm.provider_id)

    provider_orm.account_name = update.name
    _ = model_db.update_provider(session, current_user, provider_orm.id, provider_orm.to_dict())

    provider_model_orm.account_name = update.name
    provider_model_orm.model_name = update.model_name
    provider_model_orm.model_type = update.model_type
    provider_model_orm.config = {
        "apiKey": update.api_key,
        "endpointId": update.endpoint_id
    }
    provider_model_orm.capability = update.capability
    provider_model_orm = model_db.update_model(session, current_user, provider_model_orm.id,
                                               provider_model_orm.to_dict())
    return orm_to_provider_model(provider_model_orm)


def delete_model(session: Session, current_user: User, id: str) -> LLMItem:
    provider_model_orm = model_db.get_model(session, current_user, id)

    model_db.delete_provider(session, current_user, provider_model_orm.provider_id)
    model_db.delete_model(session, current_user, provider_model_orm.id)
    return orm_to_provider_model(provider_model_orm)


def set_default_llm(session: Session, current_user: User, id: str):
    model = get_provider_model()
    if model and model.is_default:
        model_db.update_model(session, current_user, model.id, {
            "is_default": False,
        })
    model_db.update_model(session, current_user, id, {
        "is_default": True,
    })


def extract_think_chain(text):
    start_tags = ['<think>', '<thinking>']
    end_tags = ['</think>', '</thinking>']
    start_index = -1
    end_index = -1
    used_start_tag = ''
    used_end_tag = ''

    for i in range(len(start_tags)):
        current_start_index = text.find(start_tags[i])
        if current_start_index != -1:
            start_index = current_start_index
            used_start_tag = start_tags[i]
            used_end_tag = end_tags[i]
            break

    if start_index == -1:
        return ''

    end_index = text.find(used_end_tag, start_index + len(used_start_tag))

    if end_index == -1:
        return ''

    return text[start_index + len(used_start_tag):end_index].strip()


def extract_answer(text):
    start_tags = ['<think>', '<thinking>']
    end_tags = ['</think>', '</thinking>']

    for i in range(len(start_tags)):
        start = start_tags[i]
        end = end_tags[i]
        if start in text and end in text:
            parts_before = text.split(start)
            parts_after = parts_before[1].split(end)
            return (parts_before[0].strip() + ' ' + parts_after[1].strip()).strip()

    return text


def extract_json_from_llm_output(output):
    # 先尝试直接 parse
    try:
        json_obj = json.loads(output)
        return json_obj
    except json.JSONDecodeError:
        pass

    json_start = output.find('```json')
    json_end = output.rfind('```')

    if json_start != -1 and json_end != -1:
        json_string = output[json_start + 7:json_end]
        try:
            json_obj = json.loads(json_string)
            return json_obj
        except json.JSONDecodeError as error:
            raise Exception(
                i18n.gettext("Error parsing JSON returned by llm. error: {error}, output: {output}").format(
                    error=error, output=output))
    else:
        raise Exception(
            i18n.gettext("The model is not output in standard format. output: {output}").format(output=output))


def get_model() -> (LLMModel, str):
    model = model_db.get_provider_model()
    if model is None:
        return None, i18n.gettext("Error: model config not found")

    llm_model = LLMModel(
        id=model.id,
        provider_name=model.provider_name,
        model_name=model.model_name,
        model_type=model.model_type,
        is_valid=model.is_valid,
        is_default=model.is_default,
        account_name=model.account_name,
        provider_id=model.provider_id,
        capability=model.capability,
        config=model.config
    )
    return llm_model, None


class ChatCotResponse(BaseModel):
    answer: str = Field(..., description="答案")
    cot: str = Field(..., description="思维链")


def chat_cot_with_error_handling(user_question: str) -> (ChatCotResponse, str):
    llm_model, err = get_model()
    if err is not None:
        return None, err
    result, err = _do_chat_cot_with_error_handling(llm_model, user_question)
    if err is not None:
        return None, err
    return result, None


def chat_with_error_handling(user_question: str) -> (dict, str):
    llm_model, err = get_model()
    if err is not None:
        return "", err
    result, err = _do_chat_with_error_handling(llm_model, user_question)
    if err is not None:
        return "", err
    return result, None


def _do_chat_cot_with_error_handling(model: LLMModel, prompt: str) -> (ChatCotResponse, str):
    try:
        client = OpenAI(api_key=model.config.apiKey, base_url=model.config.endpointId)

        # Make the API call
        response = client.chat.completions.create(
            model=model.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        # Initialize variables
        answer = ''
        cot = ''

        # Process the response
        if response.choices and response.choices[0].message:
            message = response.choices[0].message
            content = message.content or ''

            # Check for CoT patterns
            if content.startswith(('<think>', '<thinking>')):
                cot = extract_think_chain(content)
                answer = extract_answer(content)
            elif hasattr(message, 'reasoning_content'):
                cot = message.reasoning_content or ''
                answer = content
            else:
                answer = content

            # Clean up whitespace
            if answer.startswith('\n\n'):
                answer = answer[2:]
            if cot.endswith('\n\n'):
                cot = cot[:-2]
        return ChatCotResponse(
            answer=answer,
            cot=cot,
        ), None
    except RateLimitError:
        return None, i18n.gettext("Error: requests are too frequent")
    except APIConnectionError as e:
        return None, i18n.gettext("Error: requests are too frequent").format(str=str(e))
    except APIError as e:
        return None, i18n.gettext("Api call failed, status_code: {status_code}, message: {message}").format(
            status_code=e.status_code, message=e.message)
    except Exception as e:
        return None, i18n.gettext("Unexpected error. error: {error}").format(error=str(e))


def _do_chat_with_error_handling(model: LLMModel, user_question: str) -> (str, str):
    try:
        client = OpenAI(api_key=model.config.apiKey, base_url=model.config.endpointId.rstrip('/chat/completions'))

        response = client.chat.completions.create(
            model=model.model_name,
            messages=[
                # {"role": "system", "content": "你是一个有帮助的助手。"},
                {"role": "user", "content": user_question}
            ],
            temperature=0
        )
        return response.choices[0].message.content, None
    except RateLimitError:
        return None, i18n.gettext("Error: requests are too frequent")
    except APIConnectionError as e:
        return None, i18n.gettext("Error: requests are too frequent").format(str=str(e))
    except APIError as e:
        return None, i18n.gettext("Api call failed, status_code: {status_code}, message: {message}").format(
            status_code=e.status_code, message=e.message)
    except Exception as e:
        return None, i18n.gettext("Unexpected error. error: {error}").format(error=str(e))

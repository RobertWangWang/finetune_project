from fastapi.testclient import TestClient
from app.main import app  # Make sure this imports your app with all routers registered

client = TestClient(app)

def test_create_lora_argument():
    payload = {
  "additional_target": "some_module.layer1",
  "lora_alpha": 32,
  "loraplus_lr_ratio": 0.5,
  "loraplus_lr_embedding": 1e-6,
  "use_rslora": True,
  "use_dora": False,
  "pissa_init": True,
  "pissa_iter": 20,
  "pissa_convert": True,
  "create_new_adapter": True,
  "lora_dropout": 0.1,
  "lora_rank": 16,
  "lora_target": "q_proj,k_proj"
}

    response = client.post("/v1/lora_arguments/", json=payload)

    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())


if __name__ == "__main__":
    test_create_lora_argument()

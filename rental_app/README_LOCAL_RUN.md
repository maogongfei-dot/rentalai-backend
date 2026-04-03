# RentalAI — 最小运行说明

```bash
cd rental_app
pip install -r requirements.txt
```

复制 **`.env.example`** 为 **`.env`**，按需改 **HOST** / **PORT**（默认 `0.0.0.0` / `8000`）。

**PowerShell**

```powershell
cd rental_app
.\start_backend.ps1
```

**或直接 uvicorn**（工作目录须为 `rental_app`）

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

亦可用 **`python run.py`**（读取 `config` / `RENTALAI_*`）。完整变量说明见 **`.env.example`**。

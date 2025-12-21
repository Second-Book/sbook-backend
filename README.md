# textbook-marketplace-backend

### Quick manual

```
git clone https://github.com/Second-Book/textbook-marketplace-backend.git
```

```
cd textbook-marketplace-backend
```

### Download uv

#### For Linux

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### For Windows

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

### Add uv to PATH

#### For Linux

   ```
   export PATH="$HOME/.local/bin:$PATH"
   ```

#### For Windows

`Environment Variables -> Add 'C:\Users\<your_user>\.local\bin' to Path`

---

```
uv sync
```

```
source .venv/bin/activate
```

```
uv run python textbook_marketplace/manage.py migrate
```

```
uv run python textbook_marketplace/manage.py runserver
```

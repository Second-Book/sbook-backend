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

### Generate Test Data

To populate the database with realistic test data (100 textbooks, users, messages, etc.):

```
uv run python textbook_marketplace/manage.py generate_realistic_data
```

Options:
- `--textbooks N` - Number of textbooks to generate (default: 100)
- `--users N` - Number of users to generate (default: auto-calculated)
- `--skip-users` - Skip user generation if users already exist

Examples:
```
# Generate default data (100 textbooks)
uv run python textbook_marketplace/manage.py generate_realistic_data

# Generate 150 textbooks
uv run python textbook_marketplace/manage.py generate_realistic_data --textbooks 150

# Generate data without creating new users
uv run python textbook_marketplace/manage.py generate_realistic_data --skip-users
```

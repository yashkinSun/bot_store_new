# README: Telegram Bot for Digital Goods and Services Store

This bot implements the functionality of an online store with support for:

- **Digital goods** (e.g., keys, subscriptions, certificates) with online payment (via payment screenshots, payment from balance).
- **Physical goods** with order processing (delivery or self-pickup).
- **Services** (appointments for services) with application processing.

## Functional Features

### Catalog Navigation

- Selection of category, subcategory, and product/service.
- Display of product/service description with a photo.

### Order Processing

- **Digital goods**: Online purchase with balance check, uploading a payment screenshot, and administrator confirmation.
- **Physical goods**: Order placement with a choice of delivery method (delivery/self-pickup) and address specification.
- **Services**: Application submission (booking a service) with a description of the problem and application confirmation.

### Multilingual Support

- Localization (Russian and English) with the ability to switch languages via inline buttons.

### Administrative Notifications

- Automatic sending of notifications to the administrator about new orders and applications.
- Confirmation or rejection of orders/applications by the administrator via commands.

### Flexible State Management

- Use of a Finite State Machine (FSM) to organize step-by-step user interaction.

## Installation and Setup

### 1. Clone the repository:

```bash
git clone <repository_URL>
cd <project_folder>
```

### 2. Set up the virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration (config.py file):

- Specify the bot's API token, encrypted ADMIN_ID, path to the database (DB_PATH), and path to the secret key file (e.g., `/etc/bot_store_new/secret.key`).
- Configure payment details (e.g., for LTC, TRX) and other parameters.

### 4. Initialize the database:

- Run the `init_db()` function to create the tables.
- Populate the tables with demo data (e.g., call `initialize_demo_products()`).
- Create the `Categories` table and populate it:
    - Each record must contain: `id`, `safe_id`, `display_name`, and `logic_type` (e.g., 'digital', 'physical', 'appointment').
- Add products/services to the `Products` table, referencing the corresponding category via `category_id`.

### 5. Localization:

- In the `translations` folder, create or edit JSON files (e.g., `ru.json`, `en.json`) with the necessary texts.
- Update the localization dictionary (if required) in the JSON files.

### 6. Configure the category dictionary:

- In the `utils/catalog_map.py` file, edit or add new entries:

```python
CATEGORY_MAP = {
    "keys": "🔑 Keys",
    "subs": "🛒 Subscriptions",
    "misc": "🛍️ Miscellaneous",
    "certs": "🎫 Certificates",
    "services": "💼 Services",
    # Add new categories as needed
}
REVERSE_CATEGORY_MAP = {v: k for k, v in CATEGORY_MAP.items()}
```

### 7. Launch the bot:

- For manual launch:

```bash
python3 bot.py
```

- For autostart, create a systemd service (e.g., `bot.service`) and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl start bot.service
sudo systemctl enable bot.service
```

## Project Structure

- **handlers/**: Handlers for commands and callback queries:
    - `start.py`: Bot launch, welcome message.
    - `menu.py`: Main menu processing, category selection, language, etc.
    - `catalog.py`: Catalog navigation, product/service selection.
    - `purchase.py`, `order.py`, `appointment.py`: Logic for purchasing digital goods, ordering physical goods, and service applications.
    - `admin.py`: Administrative commands for confirming and rejecting orders/applications.
- **database.py**: Functions for working with the database (initialization, queries).
- **config.py**: Configuration parameters.
- **utils/**: Helper modules (localization, category dictionaries, helpers).
- **translations/**: JSON files with texts for different languages.
- **data/**: Folder with images (welcome photo, icons, photos of products and services).

## Adding New Categories, Products, and Services

### Adding a Category:

1. In the `Categories` table, insert a new record with a unique `safe_id`, `display_name`, and `logic_type` (e.g., 'digital', 'physical', 'appointment').
2. Update the `utils/catalog_map.py` file by adding the corresponding entry to `CATEGORY_MAP` (and `REVERSE_CATEGORY_MAP` will be updated automatically).

### Adding a Product/Service:

1. In the `Products` table, create a new record, specifying `category_id` (link to the corresponding category), `type` (subcategory), `name`, `description`, `price`, `photo_path`, and `quantity`.

### Localization and Menu:

1. If necessary, update the translation files in the `translations` folder.

### Logic Configuration:

1. The logic for processing a purchase, order, or service appointment is determined by the `logic_type` field in the `Categories` table. When adding a new category, make sure the correct logic is selected.

## Bot Operation Example

1. The user runs `/start` → the bot greets them and displays the main menu.
2. Category selection → subcategories are loaded (based on data from the `Categories` and `Products` tables).
3. Product/service selection → the bot displays the description, price, product photo, and buttons for further actions (purchase, order, or application).
4. When placing an order/application, the bot guides the user through sequential steps and sends notifications to the administrator.

This instruction is basic and can be supplemented depending on the individual requirements of the project. If you have any questions about configuring or extending the functionality, refer to the Aiogram and SQLite documentation or contact the developer.

## 📄 License

This project is licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0).

### What does this mean?

- ✅ You can use, modify, and distribute this software
- ✅ You can use it commercially
- ⚠️ If you modify and distribute it, you must open-source your changes
- ⚠️ If you run it as a web service, you must provide source code to users 

Full License text is available [here](https://www.gnu.org/licenses/agpl-3.0.html)

### Commercial License

If you want to use this software in a closed-source product or service,
please contact us for a commercial license: m.lanin.dev@gmail.com
# Phoenix Dev

More info:  
[Telegram Channel](https://t.me/phoenix_w3)  
[Telegram Chat](https://t.me/phoenix_w3_space)

[Инструкция на русcком](https://phoenix-14.gitbook.io/phoenix/proekty/neuraverse)</br>
[Instruction English version](https://phoenix-14.gitbook.io/phoenix/en/projects/neuraverse)</br>


## Neura 
Neura is a high-performance Layer 1 blockchain designed to support AI-driven applications and decentralized computation at scale. It combines fast execution, low fees, and modular architecture to enable seamless integration of AI agents and smart contracts. Neura’s ecosystem focuses on powering next-generation autonomous protocols while maintaining strong security and developer flexibility.


## Functionality
- Faucet 
- Bridge
- Swaps
- Portal tasks
- AI talk
- Connect social


## Requirements
- Python version 3.10 - 3.12 
- Private keys EVM
- Captcha [Capmonster](https://dash.capmonster.cloud/) for faucet
- Proxy (optional)



## Installation
1. Clone the repository:
```
git clone https://github.com/Phoenix0x-web3/neuraverse.git
cd neuraverse
```

2. Install dependencies:
```
python install.py
```

3. Activate virtual environment: </br>

`For Windows`
```
venv\Scripts\activate
```
`For Linux/Mac`
```
source venv/bin/activate
```

4. Run script
```
python main.py
```

## Project Structure
```
neuraverse/
├── data/                   #Web3 intarface
├── files/
|   ├── private_keys.txt    # Private keys EVM
|   ├── proxy.txt           # Proxy addresses (optional)
|   ├── discord_tokens.txt  # Discord tokens (optional)
|   ├── discord_proxy.txt   # Discord proxy (optional)
|   ├── twitter_tokens.txt  # Twitter tokens (optional)
|   ├── wallets.db          # Database
│   └── settings.yaml       # Main configuration file
├── functions/              # Functionality
└── utils/                  # Utils
```
## Configuration

### 1. files folder
- `private_keys.txt`: Private keys EVM
- `proxy.txt`: One proxy per line (format: `http://user:pass@ip:port`)
- `twitter_tokens.txt`: One token per line 
- `discord_tokens.txt`: One token per line 

### 2. Main configurations
```yaml
# Whether to encrypt private keys
private_key_encryption: true

# Number of threads to use for processing wallets
threads: 1

#BY DEFAULT: [0,0] - all wallets
#Example: [2, 6] will run wallets 2,3,4,5,6
#[4,4] will run only wallet 4
range_wallets_to_run: [0, 0]

# Whether to shuffle the list of wallets before processing
shuffle_wallets: true

# Working only if range_wallet_to_run = [0,0] 
# BY DEFAULT: [] - all wallets 
# Example: [1, 3, 8] - will run only 1, 3 and 8 wallets
exact_wallets_to_run: []

# Show wallet address in logs
show_wallet_address_logs: false

#Check for github updates
check_git_updates: true

# the log level for the application. Options: DEBUG, INFO, WARNING, ERROR
log_level: INFO

# Minimum native token balance in ANKR required for wallet to be processed
min_native_balance: 1

# Maximum gas price allowed for execution (in Gwei)
max_gas_price: 2500

#  Delay before running the new cycle of wallets after it has completed all actions (5 - 8 hrs default)
random_pause_wallet_after_completion:
  min: 18000
  max: 28800

# Random pause between actions in seconds
random_pause_between_actions:
  min: 5
  max: 30

# Random pause to start wallet in seconds
random_pause_start_wallet:
  min: 0
  max: 60

# Api Key from https://dash.capmonster.cloud/
capmonster_api_key: ""

```

### 3. Module Configurations

```yaml
# Onchain Swaps count
swaps_count:
  min: 5
  max: 15

# Onchain Swaps percent
swaps_percent:
  min: 25
  max: 50
  ```
```yaml
# Onchaun Bridge percent
bridge_percet:
  min: 10
  max: 20

# Onchaun Bridge count
bridge_count:
  min: 1
  max: 2
  ```
```yaml
# Number of OmniHub NFTs to mint per transaction (1 by default)
omnihub_nft_mint_count_per_transaction:
  min: 1
  max: 1

# Whether to repeat minting if NFT has already been minted before (True = retry, False = skip)
omnihub_repeat_if_already_minted: false
```
```yaml
# AI chat interactions to perform per wallet
ai_chat_count:
  min: 1
  max: 2

# List of questions that the AI can randomly ask in chat interactions 
questions_for_ai_list:
  - What is Bitcoin's current price?
  - Show me Ethereum price
  - What's the price of BNB?
 ...
```  

## Usage

For your security, you can enable private key encryption by setting `private_key_encryption: true` in the `settings.yaml`. If set to `false`, encryption will be skipped.

On first use, you need to fill in the `private_keys.txt` file once. After launching the program, go to `DB Actions → Import wallets to Database`.
<img src="https://imgur.com/IaUT1hA.png" alt="Preview" width="600"/>

If encryption is enabled, you will be prompted to enter and confirm a password. Once completed, your private keys will be deleted from the private_keys.txt file and securely moved to a local database, which is created in the files folder.

<img src="https://imgur.com/2J87b4E.png" alt="Preview" width="600"/>

If you want to update proxy/twitter/discord/email you need to make synchronize with DB. After you made changes in these files, please choose this option.

<img src="https://imgur.com/lXT6FHn.png" alt="Preview" width="600"/>

Once the database is created, you can start the project by selecting `Neuraverse → Random Activity` or any other from the list.

<img src="https://imgur.com/2CRjf81.png" alt="Preview" width="600"/>






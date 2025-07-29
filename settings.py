# Whether to encrypt private keys
PRIVATE_KEY_ENCRYPTION = True

# Number of threads to use for processing wallets
THREADS = 1

# BY DEFAULT: [] - all wallets
# Example: [1, 3, 8] -  will run only 1, 3 and 8 wallets
EXACT_WALLETS_TO_RUN = []

# Whether to shuffle the list of wallets before processing                      
SHUFFLE_WALLETS = True      
     
# Sleep time in hours after full execution of tasks
SLEEP_AFTER_EACH_CYCLE_HOURS = 0 

# Random pause between wallets in seconds
RANDOM_PAUSE_BETWEEN_WALLETS = [5, 60] 

# Random pause between actions in seconds
RANDOM_PAUSE_BETWEEN_ACTIONS = [5, 30] 

# Telegram Bot ID for notifications    
TG_BOT_ID = ''       
            
# You can find your chat ID by messaging @userinfobot or using https://web.telegram.org/.(example 1540239116)
TG_USER_ID = ''                 
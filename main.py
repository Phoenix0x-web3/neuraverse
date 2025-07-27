import asyncio
import platform

import inquirer
from colorama import Fore
from inquirer.themes import GreenPassion
from rich.console import Console
from utils.create_files import create_files
from functions.activity import activity
from functions.Import import Import


console = Console()

PROJECT = 'Base Acrhitecture'

PROJECT_ACTIONS =   [
                    "Start Testing Wallets",
                    "Start Testing Requests",
                    "Start Testing Web3",
                    "Back"
                    ]

async def choose_action():
    cat_question = [
        inquirer.List(
            "category",
            message=Fore.LIGHTBLACK_EX + 'Choose action',
            choices=[
                "DB Actions",
                PROJECT,
                "Exit"
            ],
        )
    ]

    answers = inquirer.prompt(cat_question, theme=GreenPassion())
    category = answers.get("category")

    if category == "Exit":
        console.print(f"[bold red]Exiting {PROJECT}...[/bold red]")
        raise SystemExit(0)

    if category == "DB Actions":
        actions = ["Import wallets to Database", "Back"]

    if category == PROJECT:
        actions = PROJECT_ACTIONS

    act_question = [
        inquirer.List(
            "action",
            message=Fore.LIGHTBLACK_EX + f"Choose action in '{category}'",
            choices=actions,
        )
    ]

    act_answer = inquirer.prompt(act_question, theme=GreenPassion())
    action = act_answer["action"]

    if action == "Import wallets to Database":
        console.print(f"[bold blue]Starting Import Wallets to DB[/bold blue]")
        await Import.wallets()

    elif action == "Start Testing Project":
        await activity(action=1)

    elif action == "Start Testing Requests":
        await activity(action=2)

    elif action == "Start Testing Web3":
        await activity(action=3)

    elif action == "Exit":
        console.print(f"[bold red]Exiting {PROJECT}...[/bold red]")
        raise SystemExit(0)

    await choose_action()

async def main():
    create_files()
    await choose_action()

if __name__ == '__main__':

    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
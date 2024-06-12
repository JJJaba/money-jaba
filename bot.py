import discord
from discord.ext import commands
import asyncio

# Укажите ваш токен бота
TOKEN = ''

# Создаем объект Intents
intents = discord.Intents.default()
intents.members = True  # Включаем получение информации о членах сервера
intents.message_content = True  # Включаем получение содержимого сообщений

# Создаем объект бота с префиксом команд '!' и указанием intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Словари для хранения данных о балансе и хранилищах пользователей
balances = {}
storages = {}
group_balances = {}  # Словарь для хранения общих балансов
group_roles = {}     # Словарь для хранения связей между общими балансами и ролями

@bot.event
async def on_ready():
    print(f'Бот {bot.user} подключен к серверу!')

def get_balance(user_id):
    return balances.get(user_id, 0)

def update_balance(user_id, amount):
    balances[user_id] = get_balance(user_id) + amount

def get_storage(user_id):
    return storages.get(user_id, 0)

def update_storage(user_id, amount):
    storages[user_id] = get_storage(user_id) + amount

def get_group_balance(group_name):
    return group_balances.get(group_name, 0)

def update_group_balance(group_name, amount):
    group_balances[group_name] = get_group_balance(group_name) + amount

def get_group_role(group_name):
    return group_roles.get(group_name)

# Команда !show_balances с обновлением сообщения
@bot.command(name='show_balances')
@commands.has_permissions(administrator=True)
async def show_balances(ctx, role: discord.Role):
    def create_balance_message():
        balance_message = "Баланс игроков:\n"
        for member in role.members:
            balance_message += f"{member.display_name}: {get_balance(member.id)} йен на руках, {get_storage(member.id)} йен в депозите\n"
        
        if group_balances:
            balance_message += "\nОбщие балансы:\n"
            for group_name, amount in group_balances.items():
                balance_message += f"{group_name} (роль {get_group_role(group_name).name}): {amount} йен\n"
        
        return balance_message

    # Отправляем первоначальное сообщение с балансами
    balance_message = await ctx.send(create_balance_message())

    # Обновляем сообщение каждые 10 секунд
    while True:
        await asyncio.sleep(10)
        await balance_message.edit(content=create_balance_message())

# Команда !give_money для перевода денег между пользователями
@bot.command(name='give_money')
async def give_money(ctx, recipient: discord.Member, amount: int):
    sender = ctx.author
    if amount <= 0:
        await ctx.send(f"{sender.display_name}, сумма передачи должна быть положительным числом.")
        return

    if get_balance(sender.id) < amount:
        await ctx.send(f"У {sender.display_name} недостаточно средств для передачи {amount} йен.")
        return

    update_balance(sender.id, -amount)
    update_balance(recipient.id, amount)

    await ctx.send(f"{sender.display_name} передал {amount} йен {recipient.display_name}")

# Команда !create_group_balance для создания общего баланса с названием
@bot.command(name='create_group_balance')
@commands.has_permissions(administrator=True)
async def create_group_balance(ctx, group_name: str, role: discord.Role):
    if group_name in group_balances:
        await ctx.send(f"Общий баланс с названием '{group_name}' уже существует.")
        return

    group_balances[group_name] = 0
    group_roles[group_name] = role
    await ctx.send(f"Создан общий баланс с названием '{group_name}', привязанный к роли {role.name}.")

# Команда !deposit для депозита денег
@bot.command(name='deposit')
async def deposit(ctx, amount: int):
    user = ctx.author
    if get_balance(user.id) < amount:
        await ctx.send(f"У вас недостаточно средств для депозита {amount} йен.")
        return
    update_balance(user.id, -amount)
    update_storage(user.id, amount)

    await ctx.send(f"{user.display_name} положил в хранилище {amount} йен. Баланс хранилища: {get_storage(user.id)} йен")

# Команда !withdraw для снятия денег с депозита
@bot.command(name='withdraw')
async def withdraw(ctx, amount: int):
    user = ctx.author
    if get_storage(user.id) < amount:
        await ctx.send(f"У вас недостаточно средств в хранилище для снятия {amount} йен.")
        return

    update_storage(user.id, -amount)
    update_balance(user.id, amount)

    await ctx.send(f"{user.display_name} забрал из хранилища {amount} йен. Баланс хранилища: {get_storage(user.id)} йен")

# Команда !addmoney для добавления денег пользователю (только для администраторов)
@bot.command(name='addmoney')
@commands.has_permissions(administrator=True)
async def addmoney(ctx, recipient: discord.Member, amount: int):
    update_balance(recipient.id, amount)
    await ctx.send(f"{recipient.display_name} получил {amount} йен из воздуха. Текущий баланс: {get_balance(recipient.id)} йен")

# Команда !commands для отображения списка всех команд для обычных пользователей
@bot.command(name='commands')
async def commands_list(ctx):
    commands_description = {
        'give_money': 'Переводит деньги другому игроку. Использование: !give_money @User Amount',
        'deposit': 'Кладет деньги в личное хранилище. Использование: !deposit Amount',
        'withdraw': 'Забирает деньги из личного хранилища. Использование: !withdraw Amount',
        'mybalance': 'Показывает ваш текущий баланс и депозит. Использование: !mybalance',
        'balance': 'Показывает баланс общего баланса. Использование: !balance GroupName',
        'deposit_to_group': 'Кладет деньги в общий баланс. Использование: !deposit_to_group GroupName Amount',
        'withdraw_from_group': 'Переводит деньги из общего баланса на баланс игрока. Использование: !withdraw_from_group GroupName @User Amount (Доступно только роли, привязанной к общему балансу)'
    }
    
    command_list_message = "Список доступных команд:\n"
    for command, description in commands_description.items():
        command_list_message += f"!{command} - {description}\n"

    await ctx.send(command_list_message)

# Команда !admincommands для отображения списка всех команд, доступных администраторам
@bot.command(name='admincommands')
@commands.has_permissions(administrator=True)
async def admin_commands_list(ctx):
    commands_description = {
        'show_balances': 'Показывает баланс всех игроков с определенной ролью и общие балансы. (Только для администраторов)',
        'give_money': 'Переводит деньги другому игроку. Использование: !give_money @User Amount',
        'create_group_balance': 'Создает общий баланс с названием и привязывает его к роли. Использование: !create_group_balance GroupName @Role (Только для администраторов)',
        'deposit': 'Кладет деньги в личное хранилище. Использование: !deposit Amount',
        'withdraw': 'Забирает деньги из личного хранилища. Использование: !withdraw Amount',
        'addmoney': 'Добавляет деньги пользователю. Использование: !addmoney @User Amount (Только для администраторов)',
        'mybalance': 'Показывает ваш текущий баланс и депозит. Использование: !mybalance',
        'balance': 'Показывает баланс общего баланса. Использование: !balance GroupName',
        'deposit_to_group': 'Кладет деньги в общий баланс. Использование: !deposit_to_group GroupName Amount',
        'withdraw_from_group': 'Переводит деньги из общего баланса на баланс игрока. Использование: !withdraw_from_group GroupName @User Amount (Доступно только роли, привязанной к общему балансу)',
        'commands': 'Показывает список всех доступных команд.',
        'admincommands': 'Показывает список всех команд, доступных администраторам. (Только для администраторов)'
    }
    
    command_list_message = "Список доступных команд для администраторов:\n"
    for command, description in commands_description.items():
        command_list_message += f"!{command} - {description}\n"

    await ctx.send(command_list_message)

# Команда !mybalance для отображения баланса и депозита пользователя
@bot.command(name='mybalance')
async def mybalance(ctx):
    user = ctx.author
    user_balance = get_balance(user.id)
    user_storage = get_storage(user.id)
    await ctx.send(f"{user.display_name}, ваш текущий баланс: {user_balance} йен на руках и {user_storage} йен в депозите.")

# Команда !balance для отображения баланса общего баланса
@bot.command(name='balance')
async def balance(ctx, group_name: str):
    if group_name not in group_balances:
        await ctx.send(f"Общий баланс с названием '{group_name}' не найден.")
        return

    group_balance = get_group_balance(group_name)
    role = get_group_role(group_name)
    await ctx.send(f"Общий баланс '{group_name}' (роль {role.name}): {group_balance} йен.")

# Команда !deposit_to_group для депозита в общий баланс (доступна всем, проверка роли)
@bot.command(name='deposit_to_group')
async def deposit_to_group(ctx, group_name: str, amount: int):
    user = ctx.author
    if group_name not in group_balances:
        await ctx.send(f"Общий баланс с названием '{group_name}' не найден.")
        return

    group_role = get_group_role(group_name)
    if group_role not in user.roles:
        await ctx.send(f"{user.display_name}, у вас нет роли {group_role.name}, чтобы вносить деньги в общий баланс '{group_name}'.")
        return
    
    if amount <= 0:
        await ctx.send(f"{user.display_name}, сумма депозита должна быть положительным числом.")
        return

    if get_balance(user.id) < amount:
        await ctx.send(f"У вас недостаточно средств для депозита {amount} йен в общий баланс '{group_name}'.")
        return

    update_balance(user.id, -amount)
    update_group_balance(group_name, amount)

    await ctx.send(f"{user.display_name} положил {amount} йен в общий баланс '{group_name}'. Текущий баланс общака: {get_group_balance(group_name)} йен.")

# Новая команда !withdraw_from_group для перевода денег из общего баланса на баланс игрока (доступна только роли, привязанной к общему балансу)
@bot.command(name='withdraw_from_group')
async def withdraw_from_group(ctx, group_name: str, recipient: discord.Member, amount: int):
    user = ctx.author
    if group_name not in group_balances:
        await ctx.send(f"Общий баланс с названием '{group_name}' не найден.")
        return

    group_role = get_group_role(group_name)
    if group_role not in user.roles:
        await ctx.send(f"{user.display_name}, у вас нет роли {group_role.name}, чтобы забирать деньги из общего баланса '{group_name}'.")
        return

    if amount <= 0:
        await ctx.send(f"{user.display_name}, сумма передачи должна быть положительным числом.")
        return

    if get_group_balance(group_name) < amount:
        await ctx.send(f"В общем балансе '{group_name}' недостаточно средств для передачи {amount} йен.")
        return

    update_group_balance(group_name, -amount)
    update_balance(recipient.id, amount)

    await ctx.send(f"{user.display_name} перевел {amount} йен из общего баланса '{group_name}' на баланс {recipient.display_name}. Текущий баланс общака: {get_group_balance(group_name)} йен.")

# Обработчик всех сообщений для дополнительной отладки
@bot.event
async def on_message(message):
    print(f'Получено сообщение: {message.content} от {message.author}')
    await bot.process_commands(message)  # Не забывайте обрабатывать команды

# Команда для отслеживания изменений в балансах пользователей и обновления сообщений !show_balances
@bot.event
async def on_command_completion(ctx):
    # Проверяем, вызвана ли команда !show_balances
    if ctx.command.name == 'show_balances':
        # Обновляем сообщение с балансами (здесь предполагается, что ctx отправлен для !show_balances)
        await ctx.trigger_typing()

bot.run(TOKEN)

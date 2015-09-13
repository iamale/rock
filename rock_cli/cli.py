import os
from pprint import pprint
import click
from yamlcfg import YAMLConfig
from .rocket import Rocket, RocketException
from .util import SuperDict

APP_NAME = 'rock-cli'

@click.group(context_settings={'obj': SuperDict()})
@click.pass_context
def cli(ctx):
    """
    Консольный клиент для Рокетбанка.
    """

    g = ctx.obj

    os.makedirs(click.get_app_dir(APP_NAME), exist_ok=True)
    g.config = YAMLConfig(
        paths=[os.path.join(click.get_app_dir(APP_NAME), 'config.yml')])

    g.rocket = Rocket(
        device_id=Rocket.generate_id("ROCKCLI"),
        token=g.config.token)

    def login():
        cli.commands['login'].invoke(ctx)

    g.login = login


@cli.command()
@click.option('--phone', prompt=True)
@click.pass_obj
def register(g, phone):
    rk = g.rocket
    sms = rk.register(phone)
    code = click.prompt("Введите код из SMS", type=int)
    try:
        resp = sms.verify(code)
    except RocketException as e:
        click.secho(str(e), fg='red')

    click.secho("Добро пожаловать, {}!".format(resp['user']['first_name']), fg='green')

    g.config.token = resp['token']
    g.config.email = resp['user']['email']
    g.config.write()


@cli.command()
@click.option('--password', prompt=True, hide_input=True)
@click.pass_obj
def login(g, password):
    rk = g.rocket
    email = g.config.email
    if not email:
        click.secho("Похоже, вы не авторизовывались с этого компьютера.", fg='red', bold=True)
        click.echo("Для авторизации выполните:")
        click.echo("    rock register")
        return

    try:
        resp = rk.login(email, password)
    except RocketException as e:
        click.secho(str(e), fg='red', bold=True)

    click.secho("Добро пожаловать, {}!".format(resp['user']['first_name']), fg='green')

    g.config.token = resp['token']
    g.config.write()


@cli.command()
@click.pass_obj
def tariffs(g):
    """
    Посмотреть список тарифов.
    """
    r = g.rocket.get("https://rocketbank.ru/api/v4/tariffs")
    # pprint(r.json())
    for tariff in r.json():
        click.echo("- {name} <{url}>".format(
            name=click.style(tariff['name'], fg='green', bold=True),
            url=tariff['url']))


@cli.command()
@click.pass_obj
def balance(g):
    """
    Посмотреть баланс основного счёта.
    """
    r = g.rocket.get(
        "/operations/cool_feed",
        params={'per_page': 1})
    j = r.json()

    template = "".join([
        click.style("{rur} {code}, ", fg='green', bold=True),
        "{miles} рокетрублей"])
    click.echo(template.format(
        rur=j['balance']['amount'],
        code=j['balance']['currency_code'],
        miles=int(j['miles'])))


@cli.command()
@click.option('--recipient', prompt="Получатель",
    metavar="<4242424242424242>", help="Номер карты получателя")
@click.option('--amount', prompt="Сумма (в рублях)",
    metavar="<10>", help="Сумма перевода в рублях")
@click.pass_obj
def transfer(g, recipient, amount):
    """
    Перевести деньги на номер карты.
    """
    r = g.rocket.post("/card2card/transfer", params={
      'source_card': recipient,
      'amount': amount
    })
    j = r.json()

    if j['status'] == "approved":
        template = "".join([
            click.style("{rur} {code}, ", fg='green', bold=True),
            "{miles} рокетрублей"])
        click.echo(template.format(
            rur=j['balance']['amount'],
            code=j['balance']['currency_code'],
            miles=int(j['miles'])))
    else:
        click.secho(j['errors'], fg='red', bold=True)
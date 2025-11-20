#!/usr/bin/env python3
"""
NerdNostalgia - Sistema di gestione e pubblicazione articoli su piattaforme e-commerce.

Entry point principale dell'applicazione.
"""
import click
import sys
from pathlib import Path

from src.utils.config import Config
from src.utils.logger import setup_logger
from src.parsers.csv_parser import CSVParser
from src.platforms.ebay.client import eBayClient


@click.group()
@click.option('--config', '-c', default=None, help='Path del file di configurazione')
@click.option('--verbose', '-v', is_flag=True, help='Abilita logging verbose (DEBUG)')
@click.pass_context
def cli(ctx, config, verbose):
    """
    NerdNostalgia - Gestione e pubblicazione articoli su e-commerce.
    """
    # Inizializza il contesto
    ctx.ensure_object(dict)

    # Setup logger
    log_level = "DEBUG" if verbose else "INFO"
    ctx.obj['logger'] = setup_logger(level=log_level, log_file="logs/nerdnostalgia.log")

    # Carica configurazione
    try:
        ctx.obj['config'] = Config(config)
        ctx.obj['logger'].info("Configurazione caricata con successo")
    except FileNotFoundError as e:
        ctx.obj['logger'].error(str(e))
        sys.exit(1)


@cli.command()
@click.option('--csv', '-f', required=True, help='Path del file CSV con gli articoli')
@click.option('--platform', '-p', default='ebay', help='Piattaforma target (ebay, amazon, etc.)')
@click.option('--dry-run', is_flag=True, help='Simula la pubblicazione senza pubblicare realmente')
@click.pass_context
def publish(ctx, csv, platform, dry_run):
    """
    Pubblica articoli da un file CSV su una piattaforma e-commerce.
    """
    logger = ctx.obj['logger']
    config = ctx.obj['config']

    logger.info(f"Inizio pubblicazione da {csv} su {platform}")

    # Parse CSV
    try:
        parser = CSVParser(csv)
        items = parser.parse()
        logger.info(f"Trovati {len(items)} articoli nel CSV")
    except Exception as e:
        logger.error(f"Errore nel parsing del CSV: {e}")
        sys.exit(1)

    if not items:
        logger.warning("Nessun articolo da pubblicare")
        return

    # Inizializza la piattaforma
    if platform.lower() == 'ebay':
        client = eBayClient(config.get_ebay_config())
    else:
        logger.error(f"Piattaforma '{platform}' non supportata")
        sys.exit(1)

    # Autentica
    logger.info(f"Autenticazione su {platform}...")
    if not client.authenticate():
        logger.error("Autenticazione fallita")
        sys.exit(1)

    # Pubblica articoli
    success_count = 0
    fail_count = 0

    for idx, item in enumerate(items, 1):
        logger.info(f"[{idx}/{len(items)}] Pubblicazione: {item.title[:50]}...")

        if dry_run:
            logger.info(f"  [DRY-RUN] Articolo validato: {item.title}")
            is_valid, error = client.validate_item(item)
            if is_valid:
                logger.info("  [DRY-RUN] Articolo pubblicabile")
                success_count += 1
            else:
                logger.error(f"  [DRY-RUN] Errore di validazione: {error}")
                fail_count += 1
            continue

        item_id = client.list_item(item)
        if item_id:
            logger.info(f"  ✓ Pubblicato con successo. ID: {item_id}")
            success_count += 1
        else:
            logger.error(f"  ✗ Pubblicazione fallita")
            fail_count += 1

    # Riepilogo
    logger.info("\n" + "="*60)
    logger.info(f"Pubblicazione completata:")
    logger.info(f"  ✓ Successi: {success_count}")
    logger.info(f"  ✗ Falliti: {fail_count}")
    logger.info("="*60)


@cli.command()
@click.option('--platform', '-p', default='ebay', help='Piattaforma da cui recuperare le categorie')
@click.option('--output', '-o', help='File di output per salvare le categorie (opzionale)')
@click.pass_context
def categories(ctx, platform, output):
    """
    Recupera e mostra le categorie disponibili su una piattaforma.
    """
    logger = ctx.obj['logger']
    config = ctx.obj['config']

    logger.info(f"Recupero categorie da {platform}")

    # Inizializza la piattaforma
    if platform.lower() == 'ebay':
        client = eBayClient(config.get_ebay_config())
    else:
        logger.error(f"Piattaforma '{platform}' non supportata")
        sys.exit(1)

    # Autentica
    if not client.authenticate():
        logger.error("Autenticazione fallita")
        sys.exit(1)

    # Recupera categorie
    cats = client.get_categories()

    if not cats:
        logger.warning("Nessuna categoria trovata")
        return

    logger.info(f"Trovate {len(cats)} categorie")

    # Mostra categorie
    for cat in cats[:20]:  # Mostra solo le prime 20
        logger.info(f"  {cat['id']}: {cat['name']} (Level {cat['level']})")

    if len(cats) > 20:
        logger.info(f"  ... e altre {len(cats) - 20} categorie")

    # Salva su file se richiesto
    if output:
        import json
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(cats, f, indent=2, ensure_ascii=False)
        logger.info(f"Categorie salvate in {output}")


@cli.command()
@click.argument('output_path', default='data/my_items.csv')
def init_csv(output_path):
    """
    Crea un file CSV template per iniziare ad inserire articoli.
    """
    from src.parsers.csv_parser import CSVParser
    import pandas as pd

    columns = CSVParser.get_template_columns()
    df = pd.DataFrame(columns=columns)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)

    click.echo(f"✓ Template CSV creato: {output_path}")
    click.echo(f"  Colonne: {', '.join(columns)}")
    click.echo("\nOra puoi modificare il file e aggiungere i tuoi articoli!")


@cli.command()
@click.option('--item-id', required=True, help='ID dell\'articolo da recuperare')
@click.option('--platform', '-p', default='ebay', help='Piattaforma')
@click.pass_context
def get_item(ctx, item_id, platform):
    """
    Recupera i dettagli di un articolo pubblicato.
    """
    logger = ctx.obj['logger']
    config = ctx.obj['config']

    # Inizializza la piattaforma
    if platform.lower() == 'ebay':
        client = eBayClient(config.get_ebay_config())
    else:
        logger.error(f"Piattaforma '{platform}' non supportata")
        sys.exit(1)

    # Autentica
    if not client.authenticate():
        logger.error("Autenticazione fallita")
        sys.exit(1)

    # Recupera articolo
    item = client.get_item(item_id)

    if item:
        logger.info(f"Articolo trovato:")
        logger.info(f"  Titolo: {item.title}")
        logger.info(f"  Prezzo: €{item.price}")
        logger.info(f"  Quantità: {item.quantity}")
        logger.info(f"  Condizione: {item.condition}")
    else:
        logger.error(f"Articolo {item_id} non trovato")


if __name__ == '__main__':
    cli(obj={})

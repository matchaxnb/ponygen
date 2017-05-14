#!/usr/bin/env python
"""ponygen - generate pony orm classes from an information_schema db.

Takes all times from the provided database

Usage: ponygen DSN [SCHEMA_NAME] [--outdir=<outdir>] [--engine=<engine>]

Arguments:
  DSN                The DSN to connect to, as eaten by the underlying DB-API compatible engine
  SCHEMA_NAME        Schema to generate tables for. [default: galette] 

Options:
  --engine=<engine>  DB-API compatible module to load [default: mysql]
  --outdir=<outdir>  Output directory [default: /tmp]
"""

from importlib import import_module
from itertools import groupby
import dsnparse

base_template = """
from pony import orm
db = orm.Database()
import logging

logger = logging.getLogger(__name__)

def init_mappings(prefix='', **conn_args):
{importList}
  db.bind(**conn_args)
  db.generate_mappings()
  logger.debug("done running init_mappings")

__all__ = ['db', 'init_mappings'] 
"""


class_template = """
from pony import orm
from datetime import datetime, date, time
from .ponygen import db


class {className}(db.Entity):
  _table_ = "{tableName}"
{fields}
{pk}

__all__ = ('{className}', )
"""
primaryKeyTpl = """
  orm.PrimaryKey({pkFields})
"""
field_template = """
  {fieldName} = {typeSelector}({baseType}{extraArgs})"""


def establish_conn(engine, dsn):
  db_module = import_module(engine)
  if engine in (None,):
    conn = db_module.connect(dsn)
  else:
    args = dsnparse.parse(dsn)
    argsdict = {
      'host': args.hostname or None,
      'port': args.port or None,
      'db': args.paths[0] or None,
      'user': args.username or None,
      'passwd': args.password or None,
    }
    argsdict = {a: b for a, b in argsdict.items() if b is not None}
    conn = db_module.connect(**argsdict)
  return conn

def ponygen(dsn="mysql://root@localhost/information_schema", engine="mysql", schema_name="galette", outdir="/tmp", kill_prefix="test_"):
  q = """
  SELECT TABLE_NAME as tbl, IS_NULLABLE as optional, COLUMN_NAME as col, COLUMN_TYPE as typ, COLUMN_KEY='PRI' as primarii, COLUMN_KEY='uni' as uniquei, COLUMN_KEY='mul' as non_unique, DATA_TYPE as basetype, CHARACTER_MAXIMUM_LENGTH as maxlen FROM
  INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s
  ORDER BY tbl, ORDINAL_POSITION
  """
  conn = establish_conn(engine, dsn)
  with conn.cursor() as cur:
    res = cur.execute(q, (schema_name,))
    lines = cur.fetchall()
  
  fields = list()
  mappings = list()
  for tbl_name, tbl_it in groupby(lines, key=lambda x: x[0]):
    fields = []
    pkFields = []
    # fill in template
    if kill_prefix and tbl_name.find(kill_prefix) == 0:
      tbl_name = tbl_name[len(kill_prefix):]
    table_lst = list(tbl_it)
    pk_keys = [a[2] for a in table_lst if a[4]]
    for (table_name, optional, col, typ, primary, unique, multiple, basetype, maxlen) in table_lst:
      extraArgs = []
      if primary and len(pk_keys) > 1:
        typeSelector = 'orm.Required'
        pkFields.append(col)
      elif primary and len(pk_keys) == 1:
        typeSelector = 'orm.PrimaryKey'
        pkFields = None
      elif optional:
        typeSelector = 'orm.Optional'
      else:
        typeSelector = 'orm.Required'
      if unique and not primary:
        extraArgs.append('unique=True')
      if 'blob' in basetype or basetype == 'varbinary':
        baseType = 'bytes'
      elif 'char' in basetype:
        baseType = 'str'
        extraArgs.insert(0, ', %s' % (maxlen,))
      elif 'date' == basetype:
        baseType = 'date'
      elif 'datetime' == basetype:
        baseType = 'datetime'
      elif 'time' == basetype:
        baseType = 'time'
      elif basetype in ('double', 'long'):
        baseType = 'orm.Decimal'
      elif 'int' in basetype:
        baseType = 'int'
      fields.append(field_template.format(fieldName=col, typeSelector=typeSelector, baseType=baseType, extraArgs=', '.join(extraArgs)))
    className=''.join(a.title() for a in tbl_name.split('_'))
    if pkFields:
      pk = primaryKeyTpl.format(pkFields=', '.join(pkFields))
    else:
      pk = ''
    clst = class_template.format(className=className, tableName=tbl_name, fields=''.join(fields), pk=pk)
    with open('/'.join([outdir, '.'.join([tbl_name, 'py'])]), 'w') as f:
      f.write(clst)
    mappings.append("  from .{tblName} import {className}; {className}._table_ = ''.join([prefix, {className}._table_])".format(tblName=tbl_name, className=className))
    print(clst)
  conn.close()
  with open('/'.join([outdir, '.'.join(['ponygen', 'py'])]), 'w') as f:
    f.write(base_template.format(importList="\n".join(mappings)))

if __name__ == '__main__':
  import docopt
  args = {a.lower().replace('-', ''): b for a, b in docopt.docopt(__doc__).items()}
  ponygen(**args)

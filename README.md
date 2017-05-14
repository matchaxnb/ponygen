# Ponygen - a Pony ORM class generator

Ponygen generates classes from an `information_schema` database and a given schema.

It does not support what Pony does not support.

## Nice extras

To automatically register an extension class to your PonyORM classes, use
mymodule.ponygen.ExtraClassFactory.register("MyClassName", my.module.MyOtherClass)

Table prefixes are supported. They are cleaned up at class generation and can be
specified at bind time.

## Example usage

`python ponygen.py mysql://chloe:chloe@localhost/galette galette --engine=pymysql --outdir=./outdir/`

will generate classes in outdir/

Then you have to write your `__init__.py` (an empty file does the job)

And then, do something like

```python
from outdir.ponygen import init_mappings

from outdir.ponygen import init_mappings, ExtraClassFactory

class Fooza(object):
    def blahbli(self):
        return "lel"

ExtraClassFactory.register('Adherents', Fooza)

init_mappings(prefix='test_', engine='mysql', host='localhost', user='chloe', passwd='strongpass', db='galette')

from outdir.adherents import Adherents

b = [a for a in
Adherents.select()]

b[0]
>>> Adherents[1]

 b[0].blahbli()
>>> 'lel'
```

The main attention point is to run `init_mappings` *after* you have registered your extensions.

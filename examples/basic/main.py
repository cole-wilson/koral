import jug
import js
import sys
from interface import coral_store

jug.options.set_jugdir(coral_store())

@jug.TaskGenerator
def say(number):
  js.sleep(2)
  print('finished number', number, file=sys.stderr)
  return number**3

[say(i) for i in range(1000)]

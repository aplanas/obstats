from flask import Flask
import redis

app = Flask(__name__)


@app.route('/hits/<unit>/<int:date>')
@app.route('/hits/<unit>/<int:date>/<project>')
@app.route('/hits/<unit>/<int:date>/<project>/<repository>')
@app.route('/hits/<unit>/<int:date>/<project>/<repository>/<arch>')
@app.route('/hits/<unit>/<int:date>/<project>/<repository>/<arch>/<package>')
def hits(unit, date, project=None, repository=None, arch=None, package=None):
    date_key = '%s-%s' % (date, unit)
    key = ', '.join("'%s'" % k for k in ('hits', date_key, project, repository, arch, package) if k)
    key = '(%s)' % key

    rdb = redis.Redis()
    result = rdb.get(key)
    return result if result else '0'


@app.route('/visits/<unit>/<int:date>')
@app.route('/visits/<unit>/<int:date>/<project>')
@app.route('/visits/<unit>/<int:date>/<project>/<repository>')
@app.route('/visits/<unit>/<int:date>/<project>/<repository>/<arch>')
@app.route('/visits/<unit>/<int:date>/<project>/<repository>/<arch>/<package>')
def visits(unit, date, project=None, repository=None, arch=None, package=None):
    date_key = '%s-%s' % (date, unit)
    key = ', '.join("'%s'" % k for k in ('visits', date_key, project, repository, arch, package) if k)
    key = '(%s)' % key

    rdb = redis.Redis()
    result = rdb.get(key)
    return result if result else '0'


if __name__ == '__main__':
    app.run(debug=True)

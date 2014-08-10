import cPickle as pickle
import sqlite3

class Indexer(object):
  def __init__(self, db, voc):
    """Initialize with the name of the database and a vocabulary object."""
    self.con = sqlite3.connect(db)
    self.voc = voc

  def __del__(self):
    self.con.close()

  def db_commit(self):
    self.con.commit()

  def create_tables(self):
    self.con.execute('create table imlist(filename)')
    self.con.execute('create table imwords(imid, wordid, vocname)')
    self.con.execute('create table imhistograms(imid, histogram, vocname)')

    self.con.execute('create index im_idx on imlist(filename)')
    self.con.execute('create index wordid_idx on imwords(wordid)')
    self.con.execute('create index imid_idx on imwords(imid)')
    self.con.execute('create index imidhist_idx on imhistograms(imid)')
    self.db_commit()

  def add_to_index(self, imname, descr):
    """Take an image with feature descriptors, project on vocabulary, and add to
    database."""
    if self.is_indexed(imname):
      return
    print 'indexing', imname  # FIXME: remove

    imid = self.get_id(imname)

    imwords = self.voc.project(descr)
    word_count = imwords.shape[0]

    # Link each word to image.
    for i in range(word_count):
      word = imwords[i]
      self.con.execute('insert into imwords(imid, wordid, vocname) '
          'values (?, ?, ?)', (imid, word, self.voc.name))

    # Store word histogram for image
    self.con.execute('insert into imhistograms(imid, histogram, vocname) '
        'values (?, ?, ?)', (imid, pickle.dumps(imwords), self.voc.name))

  def is_indexed(self, imname):
    im = self.con.execute(
        'select rowid from imlist where filename = ?', (imname,)).fetchone()
    return im is not None

  def get_id(self, imname):
    res = self.con.execute('select rowid from imlist where filename = ?',
                           (imname,)).fetchone()
    if res is not None:
      return res[0]
    cur = self.con.execute('insert into imlist(filename) values (?)',
                           (imname,))
    return cur.lastrowid


class Searcher(object):
  def __init__(self, db, voc):
    """Initialize with the name of the database and a vocabulary object."""
    self.con = sqlite3.connect(db)
    self.voc = voc

  def __del__(self):
    self.con.close()

  def candidates_from_word(self, imword):
    """Get list of images containing imword."""
    im_ids = self.con.execute(
        'select distinct imid from imwords where wordid = ?',
        (int(imword),)).fetchall()
    return [i[0] for i in im_ids]

  def candidates_from_histogram(self, imwords):
    """Get list of images with similar words."""
    words = imwords.nonzero()[0]
    candidates = []
    for word in words:
      candidates += self.candidates_from_word(word)

    # Take all unique words and reverse-sort on occurrence.
    tmp = [(w, candidates.count(w)) for w in set(candidates)]
    tmp.sort(key=lambda x: x[1], reverse=True)

    # Return sorted list, best matches first.
    return [w[0] for w in tmp]

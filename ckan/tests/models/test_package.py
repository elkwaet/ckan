from ckan.tests import *
import ckan.model as model

# Todo: More domain logic tests e.g. for isopen() and other domain logic.

class TestPackage:
    @classmethod
    def setup_class(self):
        self.name = u'geodata'
        self.notes = u'Written by Puccini'
        pkgs = model.Session.query(model.Package).filter_by(name=self.name).all()
        for p in pkgs:
            p.purge()
        model.Session.commit()
        rev = model.repo.new_revision()
        self.pkg1 = model.Package(name=self.name)
        model.Session.add(self.pkg1)
        self.pkg1.notes = self.notes
        self.pkg1.license_id = u'gpl-3.0'
        model.Session.commit()
        model.Session.remove()

    @classmethod
    def teardown_class(self):
        pkg1 = model.Session.query(model.Package).filter_by(name=self.name).one()
        pkg1.purge()
        model.Session.commit()
        model.Session.remove()

    def test_create_package(self):
        package = model.Package.by_name(self.name)
        assert package.name == self.name
        assert package.notes == self.notes
        assert package.license.id == u'gpl-3.0'
        assert package.license.title == u'Affero GNU Public License'
        # Check unregistered license_id causes license to be 'None'.
        package.license_id = u'zzzzzzz'
        assert package.license == None

    def test_update_package(self):
        newnotes = u'Written by Beethoven'
        author = u'jones'

        rev2 = model.repo.new_revision()
        pkg = model.Package.by_name(self.name)
        pkg.notes = newnotes
        rev2.author = u'jones'
        model.Session.commit()
        model.Session.clear()
        outpkg = model.Package.by_name(self.name)
        assert outpkg.notes == newnotes
        assert len(outpkg.all_revisions) > 0
        assert outpkg.all_revisions[0].revision.author == author


class TestPackageWithTags:
    """
    WARNING: with sqlite these tests may fail (depending on the order they are
    run in) as sqlite does not support ForeignKeys properly.
    """
    # Todo: Remove comment, since it pertains to sqlite, which CKAN doesn't support?

    @classmethod
    def setup_class(self):
        rev1 = model.repo.new_revision()
        self.tagname = u'testtagm2m'
        self.tagname2 = u'testtagm2m2'
        self.tagname3 = u'testtag3'
        self.pkgname = u'testpkgm2m'
        pkg = model.Package(name=self.pkgname)
        self.tag = model.Tag(name=self.tagname)
        self.tag2 = model.Tag(name=self.tagname2)
        pkg2tag = model.PackageTag(package=pkg, tag=self.tag)
        pkg.tags.append(self.tag2)
        model.Session.add_all([pkg,self.tag,self.tag2,pkg2tag])
        model.Session.commit()
        self.pkg2tag_id = pkg2tag.id
        self.rev = rev1

    @classmethod
    def teardown_class(self):
        # should only be one but maybe things have gone wrong
        # p = model.Package.by_name(self.pkgname)
        pkgs = model.Session.query(model.Package).filter_by(name=self.pkgname)
        for p in pkgs:
            for pt in p.package_tags:
                pt.purge()
            p.purge()
        t1 = model.Tag.by_name(self.tagname)
        t1.purge()
        t2 = model.Tag.by_name(self.tagname2)
        t2.purge()
        t3 = model.Tag.by_name(self.tagname3)
        t3.purge()
        model.Session.commit()

    def test_1(self):
        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.tags) == 2
        # pkg2tag = model.Session.query(model.PackageTag).get(self.pkg2tag_id)
        # assert pkg2tag.package.name == self.pkgname

    def test_tags(self):
        pkg = model.Package.by_name(self.pkgname)
        # TODO: go back to this
        # 2 default packages each with 2 tags so we have 2 + 4
        all = model.Session.query(model.Tag).all() 
        assert len(all) == 3, all

    def test_add_tag_by_name(self):
        rev = model.repo.new_revision()
        pkg = model.Package.by_name(self.pkgname)
        pkg.add_tag_by_name(self.tagname3)
        model.Session.commit()
        model.Session.clear()
        outpkg = model.Package.by_name(self.pkgname)
        assert len(outpkg.tags) == 3
        t1 = model.Tag.by_name(self.tagname)
        assert len(t1.package_tags) == 1

    def test_add_tag_by_name_existing(self):
        model.Session.clear()
        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.tags) == 3
        pkg.add_tag_by_name(self.tagname)
        assert len(pkg.tags) == 3


class TestPackageTagSearch:
    @classmethod 
    def setup_class(self):
        CreateTestData.create()

        model.repo.new_revision()
        self.orderedfirst = u'000-zzz'
        # tag whose association will get deleted
        self.tagname = u'russian-tag-we-will-delete'
        tag3 = model.Tag(name=self.tagname)
        pkg = model.Package.by_name(u'annakarenina')
        pkg.tags.append(tag3)
        model.repo.commit_and_remove()

        model.repo.new_revision()
        pkg = model.Package.by_name(u'annakarenina')
        # we aren't guaranteed it is last ...
        idx = [ t.name for t in pkg.tags].index(self.tagname)
        del pkg.tags[idx]
        # now do a tag for ordering
        tagordered = model.Tag(name=self.orderedfirst)
        wap = model.Package.by_name(u'warandpeace')
        # do them the wrong way round
        tagordered.packages.append(wap)
        tagordered.packages.append(pkg)
        model.repo.commit_and_remove()

    @classmethod 
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_0_deleted_package_tags(self):
        pkg = model.Package.by_name(u'annakarenina')
        tag = model.Tag.by_name(self.tagname)
        assert len(pkg.tags) == 3
        assert len(tag.packages) == 0

    def test_1_tag_search_1(self):
        out = list(model.Tag.search_by_name(u'russian'))
        assert len(out) == 2
        assert out[0].name == 'russian'

    def test_1_tag_search_2(self):
        out = list(model.Tag.search_by_name(u'us'))
        assert len(out) == 2

    def test_1_tag_search_3(self):
        out = list(model.Tag.search_by_name(u's'))
        assert len(out) == 3
    
    def test_alphabetical_ordering(self):
        pkg = model.Package.by_name(u'annakarenina')
        tag = pkg.tags_ordered[0]
        assert tag.name == self.orderedfirst, pkg.tags
        assert tag.packages_ordered[0].name == 'annakarenina', tag.packages


class TestPackageRevisions:
    @classmethod
    def setup_class(self):
        model.Session.remove()
        self.name = u'revisiontest'

        # create pkg
        self.notes = [u'Written by Puccini', u'Written by Rossini', u'Not written at all', u'Written again', u'Written off']
        rev = model.repo.new_revision()
        self.pkg1 = model.Package(name=self.name)
        model.Session.add(self.pkg1)
        self.pkg1.notes = self.notes[0]
        model.repo.commit_and_remove()

        # edit pkg
        for i in range(5)[1:]:
            rev = model.repo.new_revision()
            pkg1 = model.Package.by_name(self.name)
            pkg1.notes = self.notes[i]
            model.repo.commit_and_remove()

        self.pkg1 = model.Package.by_name(self.name)        

    @classmethod
    def teardown_class(self):
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.purge()
        model.repo.commit_and_remove()

    def test_1_all_revisions(self):
        all_rev = self.pkg1.all_revisions
        num_notes = len(self.notes)
        assert len(all_rev) == num_notes, len(all_rev)
        for i, rev in enumerate(all_rev):
            assert rev.notes == self.notes[num_notes - i - 1], '%s != %s' % (rev.notes, self.notes[i])



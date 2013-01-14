from five import grok

from Products.CMFCore.utils import getToolByName

from collective.contact.content.browser import TEMPLATES_DIR
from collective.contact.content.browser.contactable import Contactable
from collective.contact.content.organization import IOrganization


grok.templatedir(TEMPLATES_DIR)


class Organization(grok.View, Contactable):
    grok.name('organization')
    grok.context(IOrganization)
    grok.require("zope2.View")
    grok.template('organization')

    def update(self):
        self.organization = self.context
        organization = self.organization

        self.name = organization.Title()
        self.type = organization.organization_type

        self.organizations = organization.get_organizations_chain()

        catalog = getToolByName(self.context, 'portal_catalog')
        context_path = '/'.join(organization.getPhysicalPath())
        results = catalog.searchResults(path={'query': context_path,
                                              'depth': 1})
        self.items = results

        self.contactables = self.get_contactables()
        self.update_contact_details()
        self.address = self.get_address()
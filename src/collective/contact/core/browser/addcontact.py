from AccessControl import getSecurityManager
from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage
from five import grok
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.events import AddCancelledEvent
from plone.dexterity.i18n import MessageFactory as DMF
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import addContentToContainer
from plone.supermodel import model
from z3c.form import form, button
from z3c.form.contentprovider import ContentProviders
from z3c.form.interfaces import IFieldsAndContentProvidersForm, HIDDEN_MODE
from zope.component import getUtility
from zope.contentprovider.interfaces import IContentProvider
from zope.event import notify
from zope.interface import implements
from zope.publisher.browser import BrowserView

from collective.contact.widget.schema import ContactChoice
from collective.contact.widget.source import ContactSourceBinder
from collective.contact.widget.interfaces import IContactWidgetSettings

from collective.contact.core import _


class ContactWidgetSettings(grok.GlobalUtility):
    grok.implements(IContactWidgetSettings)

    def add_contact_infos(self, widget):
        source = widget.bound_source
        criteria = source.selectable_filter.criteria
        addlink_enabled = widget.field.addlink
        portal_types = criteria.get('portal_type', [])

        catalog = getToolByName(widget.context, 'portal_catalog')
        results = catalog.unrestrictedSearchResults(portal_type='directory')
        directory = results[0].getObject()

        sm = getSecurityManager()
        actions = []
        if not sm.checkPermission("Add portal content", directory):
            addlink_enabled = False

        close_on_click = True
        if addlink_enabled:
            directory_url = directory.absolute_url()
            if len(portal_types) == 1:
                addnew_url = '%s/++add++%s' % (directory_url, portal_types[0])
                fti = getUtility(IDexterityFTI, name=portal_types[0])
                type_name = fti.Title()
            else:
                addnew_url = "%s/@@add-contact" % directory_url
                type_name = _(u"Contact")
                close_on_click = False

            addlink_label = DMF(u"Add ${name}",
                    mapping={'name': type_name})

            action = {'url': addnew_url,
                      'label': addlink_label}
            actions.append(action)
        return {'actions': actions,
                'close_on_click': close_on_click,
                }

class MasterSelectAddContactProvider(BrowserView):
    implements(IContentProvider)

    def __init__(self, context, request, view):
        super(MasterSelectAddContactProvider, self).__init__(context, request)
        self.__parent__ = view

    def update(self):
        pass

    def render(self):
        # If we fill organization and person, show position and held position fields
        return """<script type="text/javascript">
$(document).ready(function() {

  $('div[id$=held_position-position]').hide();
  var position_fields = '#formfield-form-widgets-position,div[id*=held_position]';
  if (!($('input[name="form.widgets.person:list"]').length > 1 &&
        $('input[name="form.widgets.organization:list"]').length > 1)) {
      $(position_fields).hide();
 }

 function serialize_form(form) {
    viewArr = form.serializeArray(),
    view = {};
    for (var i in viewArr) {
      view[viewArr[i].name] = viewArr[i].value;
    }
    return view;
  }

  function get_selected_organization(form) {
    var view = serialize_form(form);
    var token = view['form.widgets.organization:list'];
    var title = form.find('#form-widgets-organization-input-fields input[value='+token+']').siblings('.label').find('a').first().text();
    var path = '/' + token.split('/').slice(2).join('/');
    return {token: token, title: title, path: path};
  }

  $('#form-widgets-organization-input-fields').delegate('input', 'change', function(e){
    var form = $(this).closest('form');
    var orga = get_selected_organization(form);
    var add_organization_url, addneworga, add_text;

    addneworga = $('#form-widgets-organization-autocomplete .addnew');
    if (!addneworga.data('pbo').original_src) {
        addneworga.data('pbo').original_src = addneworga.data('pbo').src;
        addneworga.data('pbo').original_text = addneworga.text();
    }
    if (orga.token == '--NOVALUE--') {
      $(position_fields).hide();
      add_organization_url = addneworga.data('pbo').original_src;
      add_text = addneworga.data('pbo').original_text;
    } else {
      // update add new orga link to add sub orga
      add_organization_url = portal_url + orga.path + '/++add++organization';
      add_text = addneworga.data('pbo').original_text + ' dans ' + orga.title;
    }
    addneworga.data('pbo').src = add_organization_url;
    addneworga.text(add_text);

    // update position autocomplete field
    $('#formfield-form-widgets-position > .fieldErrorBox').text('Recherchez ou ajoutez une fonction dans "' + orga.title + '".');
    $("#form-widgets-position-widgets-query")
        .setOptions({extraParams: {path: orga.token}}).flushCache();

    // update add new position url
    var add_position_url = portal_url + orga.path + '/++add++position';
    $('#form-widgets-position-autocomplete .addnew').data('pbo').src = add_position_url;

    // show position and held position fields if orga and person are selected
    if ($('input[name="form.widgets.person:list"]').length > 1 &&
        $('input[name="form.widgets.organization:list"]').length > 1 &&
        orga.token != '--NOVALUE--') {
      $(position_fields).show('slow');
      $('div[id$=held_position-position]').hide();
    }
  });

  $('#form-widgets-person-input-fields').delegate('input', 'change', function(e){
    if ($('input[name="form.widgets.person:list"]').length > 1 &&
        $('input[name="form.widgets.organization:list"]').length > 1) {
      $(position_fields).show('slow');
      $('div[id$=held_position-position]').hide();
    }
  });

  $('#form-widgets-position-widgets-query').setOptions({minChars: 0});
  $('#form-widgets-position-widgets-query').focus(function(e){
    $(this).trigger('click');
  });

});
</script>
"""


class IAddContact(model.Schema):
    organization = ContactChoice(
            title=_(u"Organization"),
            required=False,
            source=ContactSourceBinder(portal_type="organization"))

    person = ContactChoice(
            title=_(u"Person"),
            required=False,
            source=ContactSourceBinder(portal_type="person"))

    position = ContactChoice(
            title=_(u"Position"),
            required=False,
            source=ContactSourceBinder(portal_type="position"))


class AddContact(DefaultAddForm, form.AddForm):
    implements(IFieldsAndContentProvidersForm)
    contentProviders = ContentProviders(['organization-ms'])
#    contentProviders['organization-ms'] = MasterSelectAddContactProvider
    contentProviders['organization-ms'].position = -1
    label = DMF(u"Add ${name}", mapping={'name': _(u"Contact")})
    description = u""
    schema = IAddContact
    portal_type = 'held_position'

    @property
    def additionalSchemata(self):
        fti = getUtility(IDexterityFTI, name=self.portal_type)
        schema = fti.lookupSchema()
        # save the schema name to be able to remove a field afterwards
        self._schema_name = schema.__name__
        return (schema,)

    def updateFieldsFromSchemata(self):
        super(AddContact, self).updateFieldsFromSchemata()
        # IHeldPosition and IAddContact have both a field named position
        # hide the one from IHeldPosition
        # TODO: there is no hidden template for autocomplete widget,
        # we hide it in javascript for now.
        self.fields[self._schema_name + '.position'].mode = HIDDEN_MODE

    def updateWidgets(self):
        super(AddContact, self).updateWidgets()
        for widget in self.widgets.values():
            if getattr(widget, 'required', False):
                # This is really a hack to not have required field errors
                # but have the visual required nevertheless.
                # We need to revert this after updateActions
                # because this change impact the held position form
                widget.field.required = False

    def update(self):
        super(AddContact, self).update()
        # revert required field changes
        for widget in self.widgets.values():
            if getattr(widget, 'required', False):
                widget.field.required = True

    @button.buttonAndHandler(_('Add'), name='save')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        obj = self.createAndAdd(data)
        if obj is not None:
            # mark only as finished if we get the new object
            self._finishedAdd = True
            IStatusMessage(self.request).addStatusMessage(DMF(u"Item created"),
                                                          "info")

    @button.buttonAndHandler(DMF(u'Cancel'), name='cancel')
    def handleCancel(self, action):
        IStatusMessage(self.request).addStatusMessage(DMF(u"Add New Item operation cancelled"),
                                                      "info")
        self.request.response.redirect(self.nextURL())
        notify(AddCancelledEvent(self.context))

    def createAndAdd(self, data):
        if data['person'] is None and data['organization'] is None:
            return
        elif data['organization'] is not None and data['person'] is None:
            self.request.response.redirect(data['organization'].absolute_url())
            self._finishedAdd = True
            return
        elif data['person'] is not None and data['organization'] is None:
            self.request.response.redirect(data['person'].absolute_url())
            self._finishedAdd = True
            return
        else:
            return super(AddContact, self).createAndAdd(data)

    def create(self, data):
        self._container = data.pop('person')
        position = data.pop('position')
        orga = data.pop('organization')
        if position is None:
            position = orga

        data[self._schema_name + '.position'] = position
        return super(AddContact, self).create(data)

    def add(self, obj):
        container = self._container
        fti = getUtility(IDexterityFTI, name=self.portal_type)
        new_object = addContentToContainer(container, obj)

        if fti.immediate_view:
            self.immediate_view = "%s/%s/%s" % (container.absolute_url(),
                                                new_object.id,
                                                fti.immediate_view,)
        else:
            self.immediate_view = "%s/%s" % (container.absolute_url(),
                                             new_object.id)

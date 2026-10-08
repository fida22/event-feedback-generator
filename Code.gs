// Google Apps Script: Deploy > New deployment > Web app
// Execute as: Me | Who has access: Anyone
const TOKEN = 'CHANGE_ME_SECRET';

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    if (body.token !== TOKEN) return out({error: 'Unauthorized'});
    const spec = body.form;
    const form = FormApp.create(spec.title);
    form.setDescription(spec.description || '');
    form.setCollectEmail(false);
    spec.sections.forEach((sec, i) => {
      if (i > 0) form.addPageBreakItem().setTitle(sec.title);
      else form.addSectionHeaderItem().setTitle(sec.title);
      sec.questions.forEach(q => addQuestion(form, q));
    });
    return out({url: form.getPublishedUrl(), editUrl: form.getEditUrl()});
  } catch (err) {
    return out({error: String(err)});
  }
}

function addQuestion(form, q) {
  let item;
  const opts = (q.options || []).filter(String);
  switch (q.type) {
    case 'MULTIPLE_CHOICE':
      item = form.addMultipleChoiceItem().setChoiceValues(opts); break;
    case 'CHECKBOX':
      item = form.addCheckboxItem().setChoiceValues(opts); break;
    case 'SCALE':
      item = form.addScaleItem().setBounds(1, 5).setLabels('Poor', 'Excellent'); break;
    case 'TEXT':
      item = form.addTextItem(); break;
    default:
      item = form.addParagraphTextItem();
  }
  item.setTitle(q.text).setRequired(!!q.required);
}

function out(o) {
  return ContentService.createTextOutput(JSON.stringify(o))
    .setMimeType(ContentService.MimeType.JSON);
}

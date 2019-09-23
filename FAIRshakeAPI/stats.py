from . import models
from collections import Counter
from django.db.models import Count, Avg
from plotly import tools
import numpy as np
import plotly.graph_objs as go
import plotly.offline as opy

from scripts.linear_map import linear_map

def _iplot(*args, **kwargs):
  return opy.plot(*args, **kwargs, auto_open=False, output_type='div')

# Build Bar charts
def BarGraphs(data):
  data_dict=Counter(data)
  for x in [0,0.25,0.75,1]:
    if x not in  data_dict.keys():
      data_dict[x]=0
  if len(np.unique(data))>1:
    hist=[go.Bar(x=list(data_dict.keys()),y=list(data_dict.values()))]
    layout = go.Layout(xaxis=dict(title="FAIR score (0=no,0.25=nobut,0.5=maybe,0.75=yesbut,1=yes)",ticks='outside',tickvals=[0,0.25,0.5,0.75,1]),yaxis=dict(title='Responses'),width=400,height=400)
    fig = go.Figure(data=hist, layout=layout)
    yield _iplot(fig)

def RubricPieChart(assessments_with_rubric):
  values = assessments_with_rubric.values('rubric__title').annotate(value=Count('id')).order_by()
  rubrics, values = map(list, zip(*((val['rubric__title'], val['value']) for val in values)))
  fig = [
    go.Pie(
      labels=rubrics,
      values=values,
      hoverinfo='label+value+percent',
      textinfo='percent',
    )
  ]
  yield _iplot(fig)

def RubricsInProjectsOverlay(answers_within_project):
  rubrics = models.Rubric.objects.filter(id__in=[val['rubric'] for val in answers_within_project.values('rubric').order_by().distinct()])
  values = {
    rubric.title: list(zip(*sorted([
      (answer_count['value'], models.Answer.annotate_answer(answer_count['answers__answer'], with_perc=True))
      for answer_count in answers_within_project.filter(rubric=rubric).values('answers__answer').annotate(value=Count('answers__answer')).order_by()
    ], reverse=True)))
    for rubric in rubrics
  }
  yield _iplot({
    'data': [
      go.Bar(
        x=answers,
        y=counts,
        name=rubric
      )
      for rubric, (counts, answers) in values.items()
    ],
    'layout': {
      'xaxis': {'title': 'Answer'},
      'yaxis': {'title': 'Responses'},
      'barmode': 'stack',
    },
  })

def _QuestionBarGraphs(metric_count_dict):
  hist=[go.Bar(x=list([metric_dict[x] for x in metric_count_dict.keys()]),y=list(metric_count_dict.values()))]
  layout = go.Layout(xaxis=dict(title="Metric",titlefont=dict(size=16),tickfont=dict(size=12)),yaxis=dict(title='Mean FAIR score',titlefont=dict(size=16)))
  fig = go.Figure(data=hist, layout=layout)
  yield _iplot(fig)

def QuestionBreakdown(query):
  metric_ids=iter(np.array(query4.values_list('metric',flat=True)))
  scores=iter(np.array(query4.values_list('answer',flat=True)))
  d={}
  for x,y in zip(metric_ids,scores):
    if x in d:
      d[x] = d[x] + y 
    else:
      d[x] = y
  average_score={}
  for key, value in d.items():
    average_score[key]=value/(len(scores)/9)
  return _QuestionBarGraphs(average_score)

def DigitalObjectBarBreakdown(answers_within_project):
  # TODO: Clean this up

  colors = {
    'Poor': 'rgba(255,10,10,1)',
    'Good': 'rgba(132,0,214,1)',
    'Very FAIR': 'rgba(0,0,214,1)',
  }
  level_mapper = linear_map(
    [0, 1],
    ['Poor', 'Good', 'Very FAIR'],
  )
  values = list(sorted([
    (value['value'], value['answers__assessment__target__title'], level_mapper(value['value']))
    for value in answers_within_project.values('answers__assessment__target__title').annotate(value=Avg('answers__answer')).order_by()
  ]))
  grouped_values = {}
  for value, title, annot in values:
    if grouped_values.get(annot) is None:
      grouped_values[annot] = []
    grouped_values[annot].append((value, title))
  for annot, vals in grouped_values.items():
    grouped_values[annot] = list(zip(*vals))

  yield _iplot(
    go.Figure(
      data=[
        go.Bar(y=values, x=titles, name=annot, marker=dict(color=colors[annot]))
        for annot, (values, titles) in grouped_values.items()
      ],
      layout=go.Layout(xaxis=dict(title="Resources (n="+str(len(values))+")",showticklabels=False,titlefont=dict(size=16)),showlegend=True,yaxis=dict(title='Mean FAIR score',titlefont=dict(size=16)))
    )
  )

# Overall scores for a particular rubric, project, metric...(***Can be placed on each rubric, project, and metric page***)
# Get all scores in the database for a particular rubric, project, or metric 
# Input: Query Set (all answers), type of paramter, parameter ID
# example input query: models.Answer.objects.filter(assessment__project__id=11).all() 
def SingleQuery(querySet, PARAM, ID):
  if PARAM=="project":
    title=models.Project.objects.filter(id=ID).values_list('title', flat=True).get()
    scores=querySet.values_list('answer', flat=True)
    if len(scores)!=0:
      print("Overall FAIR Evaluations for the project:",models.Project.objects.filter(id=ID).values_list('title', flat=True).get(),"(project id:",ID,")","\n")
      print("Mean FAIR score:",round(np.mean(scores),2))
      print("Median FAIR score:",np.median(scores))
      print("Total Assessments:",len(scores)/9)
      print("Total Questions Answered:",len(scores))
      return BarGraphs(scores)
  if PARAM=="rubric":
    title=models.Rubric.objects.filter(id=ID).values_list('title', flat=True).get()
    scores=querySet.values_list('answer', flat=True)
    if len(scores)!=0:
      print("Overall FAIR Evaluations for the rubric:",models.Rubric.objects.filter(id=ID).values_list('title', flat=True).get(),"(rubric id:",ID,")","\n")
      print("Mean FAIR score:",round(np.mean(scores),2))
      print("Median FAIR score:",np.median(scores))
      print("Total Assessments:",len(scores)/9)
      print("Total Questions Answered:",len(scores))
      return BarGraphs(scores)
  if PARAM=="metric":
    title=models.Metric.objects.filter(id=ID).values_list('title', flat=True).get()
    scores=querySet.values_list('answer', flat=True)
    if len(scores)!=0:
      print("Overall FAIR Evaluations for the metric:",models.Metric.objects.filter(id=ID).values_list('title', flat=True).get(),"(metric id:",ID,")","\n")
      print("Mean FAIR score:",round(np.mean(scores),2))
      print("Median FAIR score:",np.median(scores))
      print("Total Assessments:",len(scores)/9)
      print("Total Questions Answered:",len(scores))
      return BarGraphs(scores)

def TablePlot(project):
  from django.template import Template, Context
  metrics = [
    metric.title
    for obj in project.digital_objects.all()
    for assessment in obj.assessments.all()
    for metric in assessment.rubric.metrics.all()
  ]
  objs = [
    obj.title
    for obj in project.digital_objects.all()
  ]
  scores = [
    [
      np.mean([
        answer.value()
        for answer in models.Answer.objects.filter(metric=metric, assessment__target=obj)
      ])
      for assessment in obj.assessments.all()
      for metric in assessment.rubric.metrics.all()
    ]
    for obj in project.digital_objects.all()
  ]
  trace = go.Heatmap(z=scores, x=metrics, y=objs)
  data = [trace]
  layout = go.Layout(xaxis=dict(title="Metrics",ticks='',
        showticklabels=False, automargin=True),yaxis=dict(title='Digital Objects',ticks='',
        showticklabels=True, automargin=True))
  fig = go.Figure(data=data, layout=layout)
  yield _iplot(fig)

def RubricsByMetricsBreakdown(answers_within_project):
  rubrics = models.Rubric.objects.filter(id__in=[val['rubric'] for val in answers_within_project.values('rubric').order_by().distinct()])
  values = {
    rubric.title: list(zip(*[
      (answer_count['answers__metric__title'], answer_count['value'])
      for answer_count in answers_within_project.filter(rubric=rubric).values('answers__metric__title').annotate(value=Avg('answers__answer')).order_by()
    ]))
    for rubric in rubrics
  }
  fig = tools.make_subplots(rows=len(rubrics), cols=1, print_grid=False)
  for ind, (rubric, (metrics, values)) in enumerate(values.items()):
    fig.append_trace(
      go.Bar(
        x=metrics,
        y=values,
        name=rubric
      ),
      ind+1,
      1
    )
    xaxis_num = 'xaxis%d' % (ind+1)
    fig['layout'][xaxis_num].update(showticklabels=False)
  # NOTE: this is supposed to be out of the loop
  fig['layout'][xaxis_num].update(title='Mean FAIR Score by Metric', titlefont=dict(size=16))
  yield _iplot(fig)

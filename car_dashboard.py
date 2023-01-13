# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

#Define Functions 
def style_negative(v, props=''):
    """ Style negative values in dataframe"""
    try: 
        return props if v < 0 else None
    except:
        pass
    
def style_positive(v, props=''):
    """Style positive values in dataframe"""
    try: 
        return props if v > 0 else None
    except:
        pass    

def audience_simple(country):
    """Show top represented countries"""
    if country == 'US':
        return 'USA'
    elif country == 'IN':
        return 'India'
    else:
        return 'Other'
    
@st.cache(allow_output_mutation=True)
def load_data():  
    df_agg = pd.read_csv('export_car_df.csv')
    df_agg['Transaction Date'] = pd.to_datetime(df_agg['Transaction Date'])
    df_agg.dropna(inplace=True)
    df_agg["Reference Price (HKD)"] = df_agg["Reference Price (HKD)"].replace('[\$,]', '', regex=True).astype(int)
    df_agg['No. of Previous Owners'] = pd.to_numeric(df_agg['No. of Previous Owners'], errors='coerce')
    df_agg['No. of Previous Owners'] = df_agg['No. of Previous Owners'] + 1
    df_agg['Age'] = pd.DatetimeIndex(df_agg['Transaction Date']).year-df_agg['Manufacture Year']
    
    return df_agg
#create dataframes from the function 
df_agg = load_data()
source_top10 = df_agg['Car Brand'].value_counts().rename_axis('Car Brand').reset_index(name='Counts')
###############################################################################
#Start building Streamlit App
###############################################################################
v_width=500
v_height=380

add_sidebar = st.sidebar.selectbox('Analysis Selection', ('Aggregate Metrics','Aggregate Graphic','Individual Car Brand Analysis'))

#Show individual metrics 
if add_sidebar == 'Aggregate Metrics':

    
    #additional data engineering for aggregated data 
    df_agg_diff = df_agg[['Transaction Date','Car Brand','Car Model','Exterior Color','Displacement (c.c.)','Manufacture Year','Age','No. of Previous Owners','Milleage (km)','Reference Price (HKD)']].copy()
    metric_date_12mo = df_agg_diff['Transaction Date'].max() - pd.DateOffset(months =12)
    median_agg = df_agg_diff[df_agg_diff['Transaction Date'] >= metric_date_12mo].median()

    #create differences from the median for values 
    #Just numeric columns 
    numeric_cols = np.array((df_agg_diff.dtypes == 'float64') | (df_agg_diff.dtypes == 'int32'))
    df_agg_diff.iloc[:,numeric_cols] = (df_agg_diff.iloc[:,numeric_cols] - median_agg).div(median_agg)

    
    st.write("% Changes of 1 Month to 12 Months Aggregated Data")
    df_agg_metrics = df_agg[['Transaction Date','Displacement (c.c.)','Manufacture Year','Age','No. of Previous Owners','Milleage (km)','Reference Price (HKD)']]
    metric_date_1mo = df_agg_metrics['Transaction Date'].max() - pd.DateOffset(months = 1)
    metric_date_12mo = df_agg_metrics['Transaction Date'].max() - pd.DateOffset(months = 12)
    metric_medians1mo = df_agg_metrics[df_agg_metrics['Transaction Date'] >= metric_date_1mo].median()
    metric_medians12mo = df_agg_metrics[df_agg_metrics['Transaction Date'] >= metric_date_12mo].median()

    col1, col2, col3, col4, col5 = st.columns(5)
    columns = [col1, col2, col3, col4, col5]
    df_agg_metrics.info()
    count = 0
    for i in metric_medians1mo.index:
        with columns[count]:
            delta = (metric_medians1mo[i] - metric_medians12mo[i])/metric_medians12mo[i]
            if 'Price' in i:
                st.metric(label= i, value = str(int(metric_medians1mo[i]/1000)) + 'K' , delta = "{:.2%}".format(delta))
            else:
                st.metric(label= i, value = int(metric_medians1mo[i]), delta = "{:.2%}".format(delta))
            count += 1
            if count >= 3:
                count = 0
                
    df_agg_numeric_lst = df_agg_diff.median().index.tolist()
    df_to_pct = {}  
    for i in df_agg_numeric_lst:
        df_to_pct[i] = '{:.1%}'.format
    
    st.dataframe(df_agg_diff.style.hide().applymap(style_negative, props='color:red;').applymap(style_positive, props='color:green;').format(df_to_pct))
  
    
   # st.altair_chart(base, use_container_width=True)
if add_sidebar == 'Aggregate Graphic':

    source2 = df_agg['Transaction Date'].value_counts().rename_axis('Transaction Date').reset_index(name='Counts')

    base = alt.Chart(source2,title="Number Of Transactions Per Month").mark_area(
        color='goldenrod',
        opacity=0.3
    ).encode(
        x='yearmonth(Transaction Date):Q',
        y='Counts:Q',
    ).properties(
    width=v_width,
    height=v_height
    )
    
    brush = alt.selection_interval(encodings=['x'],empty='all')
    background = base.add_selection(brush)
    selected = base.transform_filter(brush).mark_area(color='goldenrod')
    
    background + selected
    
        
    # Chart for Top 10 Car Brands in Transaction (Descending)
    
    bar_chart = alt.Chart(source_top10,title="Top 10 Car Brands in Transaction").mark_bar().encode(
        x=alt.X('Car Brand:N', sort='-y'),
        y='Counts'
    ).transform_window(
    rank='rank(Counts)',
    sort=[alt.SortField('Counts', order='descending')]
    ).transform_filter(
    (alt.datum.rank <= 10)
    )
    
    bar_chart = bar_chart.properties(
    width=v_width,
    height=v_height
    )
    bar_chart
    # st.altair_chart(bar_chart, use_container_width=True)
    
    # Heatmap Chart
    cor_data = (df_agg.corr().stack().reset_index().rename(columns={0: 'correlation', 'level_0': 'var1', 'level_1': 'var2'}))
    cor_data['correlation_label'] = cor_data['correlation'].map('{:.2f}'.format)  # Round to 2 decimal
    cor_data.head()
    
    base = alt.Chart(cor_data,title="Heatmap").transform_filter(
    alt.datum.var1 < alt.datum.var2
    ).encode(
    x='var1:O',
    y='var2:O'
    )
    # Text layer with correlation labels
    # Colors are for easier readability
    text = base.mark_text().encode(
        text='correlation_label',
        color=alt.condition(
            alt.datum.correlation > 0.5, 
            alt.value('white'),
            alt.value('black')
        )
    )

    # The correlation heatmap itself
    cor_plot = base.mark_rect().encode(
        color=alt.Color(
        "correlation:Q",
        scale=alt.Scale(
            scheme="redblue",
            reverse=False
            )
        )
    ).properties(
    width=v_width,
    height=v_height
    )
    
    cor_plot + text # The '+' means overlaying the text and rect layer
    # st.altair_chart(cor_plot + text, use_container_width=True)
    

    ##### Here is the code used to create interval selection and scatter plot ##### 
    df_agg['Engine Size Category']=pd.cut(df_agg['Displacement (c.c.)'], bins=[0, 800, 1000, 1400, 1600, 2000, 3000, 5000], include_lowest=False).astype(str)
    df_agg.info()
    brush = alt.selection(type="interval")
    car_brand_select = alt.selection(type='single', fields=['Car Brand'])
    points = (
        alt.Chart(df_agg)
        .mark_point() # Create scatter plot
        .encode(
            x="Age:Q",
            y="Milleage (km):Q",
            tooltip=["Reference Price (HKD)", "Age", "Milleage (km)","Engine Size Category"],
            # color=alt.condition(brush, "Engine Size Category:N", alt.value("lightgray")),
        )
        .add_selection(brush)
    ).properties(    
        width=v_width,
        height=v_height,
       )

    ##### Here is the code used to create interval selection and scatter plot ##### 
    # Create bar plot that responds to interval selection
    bars = (
        alt.Chart(df_agg)
        .mark_bar() # Create bar plot
        .encode(
            y=alt.Y('Car Brand:N', sort='-x'),
            color=alt.Color("Car Brand:N"),
            x="count(Car Brand):Q",
        ).properties(
            selection=car_brand_select)
         .transform_filter(brush)
    )

    # # Concatenate bar plot and scatter plot vertically
    chart = alt.vconcat(points, bars).properties(
        title="Click and drag in the scatter plot to create a selection region"
    )
    chart
    
if add_sidebar == 'Individual Car Brand Analysis':
    
    brands = tuple(source_top10['Car Brand'][0:10])
    st.write("Individual Car Brand")
    brand_select = st.selectbox('Pick a Brand:', brands)
    
    agg_filtered = df_agg[df_agg['Car Brand'] == brand_select]
    
    bar = alt.Chart(agg_filtered).mark_bar().encode(
    x=alt.X('count(Exterior Color)', stack="normalize"),
    y='Car Brand',
    color=alt.Color("Exterior Color:N"),
    tooltip=alt.Tooltip("count(Exterior Color)", format=",.0f")
    ).properties(    
        width=v_width,
        height=v_height
       )
    bar

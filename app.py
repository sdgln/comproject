# -*- coding: utf-8 -*-
"""app

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1F1whA512tnPg-v5T0CkbrFO47uRh4yf_
"""

# 1. Import libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GridSearchCV, learning_curve, train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import warnings
warnings.filterwarnings("ignore")

# 2. Load dataset
import kagglehub
rohitsahoo_sales_forecasting_path = kagglehub.dataset_download('rohitsahoo/sales-forecasting')
print('Data source import complete.')

# Load and process data
df = pd.read_csv('/kaggle/input/sales-forecasting/train.csv')
df['Order Date'] = pd.to_datetime(df['Order Date'], dayfirst=True)
df = df.sort_values('Order Date')
df.set_index('Order Date', inplace=True)

#log transform
df['Sales'] = np.log1p(df['Sales'])
# Monthly aggregated sales
monthly_sales = df.resample('M').sum()['Sales']

# Basic statistics and outlier removal
mean = monthly_sales.mean()
median = monthly_sales.median()
Q1 = monthly_sales.quantile(0.25)
Q3 = monthly_sales.quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

# 1. Box Plot with Annotations
plt.figure(figsize=(10, 4))
box = plt.boxplot(monthly_sales, vert=False, patch_artist=True,
                  boxprops=dict(facecolor='lightblue', color='navy'),
                  medianprops=dict(color='red'),
                  flierprops=dict(marker='o', markerfacecolor='orange', markersize=6))

plt.title('Box Plot of Monthly Sales')
plt.xlabel('Sales ($)')
plt.grid(True)

# Add annotations
plt.axvline(mean, color='green', linestyle='--', linewidth=1)
plt.text(mean, 1.1, 'Mean', color='green', ha='center', fontsize=9)

plt.axvline(median, color='red', linestyle='-', linewidth=1)
plt.text(median, 0.85, 'Median', color='red', ha='center', fontsize=9)

plt.text(Q1, 1.15, 'Q1', color='blue', ha='center', fontsize=9)
plt.text(Q3, 1.15, 'Q3', color='blue', ha='center', fontsize=9)
plt.text((Q1 + Q3) / 2, 1.2, f'IQR: {IQR:.0f}', color='black', ha='center', fontsize=9)

plt.show()

outliers = monthly_sales[(monthly_sales < lower_bound) | (monthly_sales > upper_bound)]
monthly_sales_cleaned = monthly_sales.copy()
monthly_sales_cleaned[(monthly_sales < lower_bound) | (monthly_sales > upper_bound)] = mean

# Charts for outlier visualization
plt.figure(figsize=(10, 4))
plt.boxplot([monthly_sales, monthly_sales_cleaned], vert=False, patch_artist=True,
            boxprops=dict(facecolor='lightblue'), medianprops=dict(color='red'))
plt.yticks([1, 2], ['Original', 'Cleaned'])
plt.title('Outlier Detection Before and After Cleaning')
plt.xlabel('Sales')
plt.grid(True)
plt.show()

# Plot raw vs cleaned data
plt.figure(figsize=(12, 4))
plt.plot(monthly_sales, label='Original', alpha=0.5)
plt.plot(monthly_sales_cleaned, label='Cleaned', linestyle='--')
plt.title('Monthly Sales: Raw vs. Cleaned')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()


# Describe cleaned data
overview = monthly_sales_cleaned.describe()
extra_stats = {
    'variance': monthly_sales_cleaned.var(),
    'median': monthly_sales_cleaned.median(),
    'iqr': monthly_sales_cleaned.quantile(0.75) - monthly_sales_cleaned.quantile(0.25),
    'skewness': monthly_sales_cleaned.skew(),
    'kurtosis': monthly_sales_cleaned.kurt()
}
extra_stats_df = pd.Series(extra_stats)
full_overview = pd.concat([overview, extra_stats_df])
print("Statistical Overview (After Outlier Replacement):\n")
print(full_overview)

"""We replaced the outliers with the mean to prevent them from negatively affecting the overall analysis. Since the mean shows the general level of the data, using it helps us keep the dataset consistent without letting extreme values create misleading results. This way, we didn’t delete any data points, but we reduced their impact."""

# Seasonality check: average sales by month
df['Month'] = df.index.month
monthly_avg = df.groupby('Month')['Sales'].mean()
monthly_avg.plot(kind='bar', figsize=(8, 4), title='Average Sales by Month')
plt.ylabel('Average Sales ($)')
plt.xlabel('Month')
plt.grid(True)
plt.show()

# Seasonal decomposition
from statsmodels.tsa.seasonal import seasonal_decompose
result = seasonal_decompose(monthly_sales_cleaned, model='additive', period=12)
result.plot()
plt.suptitle("Seasonal Decomposition of Monthly Sales", fontsize=16)
plt.tight_layout()
plt.show()

# Moving averages
ma3 = monthly_sales_cleaned.rolling(window=3).mean()
ma6 = monthly_sales_cleaned.rolling(window=6).mean()
plt.figure(figsize=(12,4))
plt.plot(monthly_sales_cleaned, label='Actual')
plt.plot(ma3, label='MA(3)', linestyle='--')
plt.plot(ma6, label='MA(6)', linestyle=':')
plt.title('Moving Averages (3 and 6 months)')
plt.grid(True)
plt.legend()
plt.show()

"""Based on the seasonal decomposition of the monthly sales data, it is evident that the time series contains both a trend and a seasonal component. The trend component shows a generally increasing pattern, especially after 2015, which indicates a long-term growth in sales. Additionally, the seasonal component reveals repeating fluctuations within the same months each year, confirming the presence of seasonality in the data. These findings suggest that models like Holt-Winters or SARIMA, which can capture both trend and seasonality, would be more appropriate for forecasting tasks than models without seasonal adjustment."""

# SES and Holt-Winters
from statsmodels.tsa.holtwinters import SimpleExpSmoothing, ExponentialSmoothing
ses_model = SimpleExpSmoothing(monthly_sales_cleaned).fit(smoothing_level=0.2, optimized=False)
ses_forecast = ses_model.fittedvalues
plt.figure(figsize=(12,4))
plt.plot(monthly_sales_cleaned, label='Actual')
plt.plot(ses_forecast, label='SES (alpha=0.2)', linestyle='--')
plt.title('Simple Exponential Smoothing')
plt.grid(True)
plt.legend()
plt.show()

hw_model = ExponentialSmoothing(monthly_sales_cleaned, trend='add', seasonal='add', seasonal_periods=12).fit()
hw_forecast = hw_model.fittedvalues
plt.figure(figsize=(12,4))
plt.plot(monthly_sales_cleaned, label='Actual')
plt.plot(hw_forecast, label='Holt-Winters', linestyle='--')
plt.title('Holt-Winters Forecast')
plt.grid(True)
plt.legend()
plt.show()

# Auto ARIMA
#!pip install numpy==1.24.3 pmdarima --force-reinstall --no-cache-dir
import pmdarima as pm
auto_model = pm.auto_arima(
    monthly_sales_cleaned,
    seasonal=True,
    m=12,
    trace=True,
    stepwise=True,
    suppress_warnings=True
)
print(auto_model.summary())
fitted_values = pd.Series(auto_model.predict_in_sample(), index=monthly_sales_cleaned.index)
plt.figure(figsize=(12, 4))
plt.plot(monthly_sales_cleaned, label='Actual')
plt.plot(fitted_values, label='Auto ARIMA Fitted', linestyle='--')
plt.title('Auto ARIMA/SARIMA Forecast')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

# Random Forest with lag features
df_ml = monthly_sales_cleaned.to_frame().copy()
df_ml['lag1'] = df_ml['Sales'].shift(1)
df_ml['lag2'] = df_ml['Sales'].shift(2)
df_ml.dropna(inplace=True)
X = df_ml[['lag1', 'lag2']]
y = df_ml['Sales']
X_train, X_test = X.iloc[:int(0.8*len(X))], X.iloc[int(0.8*len(X)):]
y_train, y_test = y.iloc[:int(0.8*len(X))], y.iloc[int(0.8*len(X)):]

# Pipeline and GridSearchCV
pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('model', RandomForestRegressor())
])
param_grid = {
    'model__n_estimators': [50, 100],
    'model__max_depth': [5, 10, None]
}
search = GridSearchCV(pipeline, param_grid, cv=5, scoring='neg_mean_squared_error')
search.fit(X_train, y_train)
best_rf_model = search.best_estimator_
y_pred_rf = best_rf_model.predict(X_test)
print("\n--- Random Forest Performance ---")
print("MAE:", mean_absolute_error(y_test, y_pred_rf))
print("RMSE:", np.sqrt(mean_squared_error(y_test, y_pred_rf)))
print("R2:", r2_score(y_test, y_pred_rf))

# Plotting the actual vs predicted sales from Random Forest
plt.figure(figsize=(12,4))
plt.plot(y_test.index, y_test, label='Actual Sales', marker='o')
plt.plot(y_test.index, y_pred_rf, label='Random Forest Prediction', linestyle='--', color='orange')
plt.title("Random Forest Regression Forecast vs Actuals")
plt.xlabel("Date")
plt.ylabel("Sales ($)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

#Feature Importance Plot
importances = best_rf_model.named_steps['model'].feature_importances_
features = X.columns
plt.barh(features, importances)
plt.title("Feature Importances - Random Forest")
plt.xlabel("Importance")
plt.grid(True)
plt.tight_layout()
plt.show()

#Train/Test Residual Plot
residuals = y_test - y_pred_rf
plt.scatter(y_test, residuals)
plt.axhline(0, color='red', linestyle='--')
plt.title('Residual Plot - Random Forest')
plt.xlabel('Actual')
plt.ylabel('Residuals')
plt.grid(True)
plt.show()

# Learning Curve
train_sizes, train_scores, val_scores = learning_curve(
    RandomForestRegressor(), X, y, cv=5, scoring='neg_mean_squared_error')
train_error = -np.mean(train_scores, axis=1)
val_error = -np.mean(val_scores, axis=1)
plt.figure(figsize=(10, 4))
plt.plot(train_sizes, train_error, label='Train Error')
plt.plot(train_sizes, val_error, label='Validation Error')
plt.title('Learning Curve - Random Forest')
plt.xlabel('Training Size')
plt.ylabel('MSE')
plt.legend()
plt.grid(True)
plt.show()

# Voting Regressor
voting = VotingRegressor(estimators=[
    ('rf', RandomForestRegressor()),
    ('lr', LinearRegression()),
    ('gb', GradientBoostingRegressor())
])
voting.fit(X_train, y_train)
y_pred_vote = voting.predict(X_test)
print("\n--- Voting Regressor Performance ---")
print("MAE:", mean_absolute_error(y_test, y_pred_vote))
print("RMSE:", np.sqrt(mean_squared_error(y_test, y_pred_vote)))
print("R2:", r2_score(y_test, y_pred_vote))

#Linear Regression Baseline
lr = LinearRegression()
lr.fit(X_train, y_train)
y_pred_lr = lr.predict(X_test)
print("Linear Regression MAE:", mean_absolute_error(y_test, y_pred_lr))

from statsmodels.tsa.holtwinters import ExponentialSmoothing
import matplotlib.pyplot as plt

# Fit the Holt-Winters model using the cleaned dataset
# We use additive trend and additive seasonality with monthly seasonality (period=12)
hw_model = ExponentialSmoothing(
    monthly_sales_cleaned,
    trend='add',
    seasonal='add',
    seasonal_periods=24
).fit()

# Forecast the next 12 months (1 year)
forecast_24 = hw_model.forecast(24)

# Plot actual vs forecasted values
plt.figure(figsize=(12, 4))
plt.plot(monthly_sales_cleaned, label='Actual')
plt.plot(forecast_24, label='Forecast (Next 24 Months)', linestyle='--', color='orange')
plt.title('Holt-Winters 2-Year Forecast')
plt.xlabel('Date')
plt.ylabel('Sales ($)')
plt.grid(True)
plt.legend()
plt.show()

"""In this project, we applied several time series forecasting techniques including moving average (MA(3) and MA(6)), Simple Exponential Smoothing (SES), Holt-Winters, and Auto ARIMA to model the monthly sales data. The time series analysis revealed the presence of both trend and seasonality, making seasonal models more suitable. Among the models tested, Holt-Winters and Auto ARIMA delivered the most accurate forecasts, as illustrated in the cross-validation error comparison chart. These models effectively captured the repeating seasonal behavior and overall growth trend in the data. The results emphasize the importance of selecting models that align with the underlying structure of the time series, especially when both trend and seasonality are present."""

# Cross-validation comparison of models
initial_train_size = len(monthly_sales_cleaned) - 12
horizon = 1
n_splits = 12

def mape(y_true, y_pred):
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

models_to_test = ['MA(3)', 'MA(6)', 'SES', 'Holt-Winters', 'Auto ARIMA']
cv_results = {'Model': [], 'MAE': [], 'RMSE': [], 'MAPE': []}

for model_name in models_to_test:
    mae_list, rmse_list, mape_list = [], [], []

    for i in range(n_splits):
        train_end = initial_train_size + i
        train_data = monthly_sales_cleaned[:train_end]
        test_data = monthly_sales_cleaned[train_end:train_end + horizon]

        try:
            if model_name == 'MA(3)':
                pred = train_data.rolling(window=3).mean().iloc[-1]
                forecast = np.repeat(pred, horizon)
            elif model_name == 'MA(6)':
                pred = train_data.rolling(window=6).mean().iloc[-1]
                forecast = np.repeat(pred, horizon)
            elif model_name == 'SES':
                model = SimpleExpSmoothing(train_data).fit(smoothing_level=0.2, optimized=False)
                forecast = model.forecast(horizon)
            elif model_name == 'Holt-Winters':
                model = ExponentialSmoothing(train_data, trend='add', seasonal='add', seasonal_periods=12).fit()
                forecast = model.forecast(horizon)
            elif model_name == 'Auto ARIMA':
                model = pm.auto_arima(train_data, seasonal=True, m=12, suppress_warnings=True)
                forecast = model.predict(n_periods=horizon)

            mae_list.append(mean_absolute_error(test_data, forecast))
            rmse_list.append(np.sqrt(mean_squared_error(test_data, forecast)))
            mape_list.append(mape(test_data, forecast))
        except:
            print(f"Model {model_name} failed at step {i}")
            break

    cv_results['Model'].append(model_name)
    cv_results['MAE'].append(np.mean(mae_list))
    cv_results['RMSE'].append(np.mean(rmse_list))
    cv_results['MAPE'].append(np.mean(mape_list))

cv_results_df = pd.DataFrame(cv_results)
print("\nCross-Validation Error Comparison:")
print(cv_results_df)

# Bar chart for model comparison
x = np.arange(len(cv_results_df))
bar_width = 0.25
plt.figure(figsize=(14, 6))
bars1 = plt.bar(x - bar_width, cv_results_df['MAE'], width=bar_width, label='MAE')
bars2 = plt.bar(x, cv_results_df['RMSE'], width=bar_width, label='RMSE')
bars3 = plt.bar(x + bar_width, cv_results_df['MAPE'], width=bar_width, label='MAPE')

for bar in bars1 + bars2 + bars3:
    height = bar.get_height()
    plt.annotate(f'{height:.1f}',
                 xy=(bar.get_x() + bar.get_width() / 2, height),
                 xytext=(0, 3),
                 textcoords="offset points",
                 ha='center', va='bottom', fontsize=9)

plt.xticks(x, cv_results_df['Model'], rotation=15)
plt.title('Forecasting Model Error Comparison (Cross-Validation)', fontsize=14)
plt.ylabel('Error Value')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.show()

# Save best model
joblib.dump(best_rf_model, 'best_rf_forecast_pipeline.pkl')

loaded_model = joblib.load('best_rf_forecast_pipeline.pkl')
prediction = loaded_model.predict(X_test)

# Commented out IPython magic to ensure Python compatibility.
# # streamlit_app.py
# !pip install streamlit localtunnel
# %%writefile app.py
# # paste your full streamlit code here (the same one you already wrote)
# !streamlit run app.py & npx localtunnel --port 8501
# 
# import streamlit as st
# import pandas as pd
# import matplotlib.pyplot as plt
# 
# st.set_page_config(page_title="Sales Forecasting App", layout="wide")
# st.title("📈 Sales Forecasting App")
# 
# uploaded_file = st.file_uploader("Upload your sales CSV file (with 'Order Date' and 'Sales')")
# 
# if uploaded_file:
#     df = pd.read_csv(uploaded_file)
# 
#     try:
#         df['Order Date'] = pd.to_datetime(df['Order Date'], dayfirst=True)
#         df = df.sort_values('Order Date')
#         df.set_index('Order Date', inplace=True)
# 
#         monthly_sales = df.resample('M').sum()['Sales']
# 
#         st.subheader("📊 Monthly Sales Chart")
#         st.line_chart(monthly_sales)
# 
#         st.subheader("📈 3-Month Moving Average")
#         ma3 = monthly_sales.rolling(3).mean()
#         st.line_chart(ma3)
# 
#         st.subheader("📋 Statistical Summary")
#         st.write(monthly_sales.describe())
# 
#         st.subheader("🔍 Outlier Detection")
#         Q1 = monthly_sales.quantile(0.25)
#         Q3 = monthly_sales.quantile(0.75)
#         IQR = Q3 - Q1
#         lower_bound = Q1 - 1.5 * IQR
#         upper_bound = Q3 + 1.5 * IQR
#         outliers = monthly_sales[(monthly_sales < lower_bound) | (monthly_sales > upper_bound)]
#         st.write(f"Detected {len(outliers)} outliers:")
#         st.write(outliers)
# 
#     except Exception as e:
#         st.error(f"⚠️ Error processing file: {e}")
# else:
#     st.info("Please upload a CSV file to begin.")
#
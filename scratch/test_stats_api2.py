import traceback
try:
    from services.statistics_engine import StatisticsEngine
    print(StatisticsEngine.get_all_time_kpis())
except Exception as e:
    print('ERROR:', type(e), str(e))
    traceback.print_exc()

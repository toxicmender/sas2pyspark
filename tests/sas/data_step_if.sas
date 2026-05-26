data sales_final;
    set sales_2024;
    if revenue > 1000 then category='HIGH';
    else category='LOW';
run;

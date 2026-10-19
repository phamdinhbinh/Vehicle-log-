from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from vehiclelog.formulas import align_values, evaluate_all, evaluate_formula, evaluate_trace, validate_expression
from vehiclelog.models import CancellationToken, CancelledError, Formula, Segment, SignalInfo


class MemoryStore:
    def __init__(self, signals):
        self.data = {key:(np.asarray(t,dtype=float),np.asarray(v,dtype=float)) for key,(t,v,_) in signals.items()}
        self.signals = {key:SignalInfo(key,key,unit) for key,(_,_,unit) in signals.items()}
        self.reads=[]

    def read(self,key,start=None,end=None,neighbors=False):
        self.reads.append((key,start,end,neighbors))
        return self.data[key]


def calculate(expression,signals,*,start=0,end=2,interpolation="hold",max_gap=2,unit=""):
    store=MemoryStore(signals)
    segment=Segment("test",start,end)
    formula=Formula("test",expression,{key:key for key in signals},unit,[segment.id],interpolation,max_gap)
    return evaluate_formula(store,formula,segment)


@pytest.mark.parametrize("text",[
    "__import__('os').system('true')", "U.__class__", "U[0]", "[U]", "lambda: U",
    "integral(U, I)","integral(integral(U))","U ** U","U ** 100","sum(U)",
    "1e309", "True", "clip(U, low=0, high=1)", "(x for x in U)",
])
def test_unsafe_or_unsupported_expressions_rejected(text):
    with pytest.raises(ValueError):
        validate_expression(text,{"U":"u","I":"i"})


def test_alias_validation_and_unknown_reference():
    for expression,aliases in [("X",["U"]),("1",["_bad"]),("1",["integral"])]:
        with pytest.raises(ValueError):
            validate_expression(expression,aliases)
    validate_expression("integral(positive(U * I)) / 3600000",["U","I"])


def test_hold_timestamp_integral_and_time_weighted_mean():
    data={"X":([0,.2,2],[10,20,100],"")}
    assert calculate("integral(X)",data).value == pytest.approx(38.)
    assert calculate("mean(X)",data).value == pytest.approx(19.)
    assert calculate("sample_mean(X)",data).value == pytest.approx(130/3)
    assert calculate("last(X)-first(X)",data).value == pytest.approx(90.)
    assert calculate("delta(X)",data).value == pytest.approx(90.)


def test_linear_product_energy_matches_analytic_integral():
    # U=300+10t, I=10-10t; U*I=3000-2900t-100t².
    data={"U":([0,2],[300,320],"V"),"I":([0,1,2],[10,0,-10],"A")}
    result=calculate("integral(U * I)",data,interpolation="linear",unit="J")
    assert result.status == "ok",result.message
    assert result.value == pytest.approx(-200/3,abs=1e-9)
    discharge=calculate("integral(positive(U*I))",data,interpolation="linear",unit="J")
    regen=calculate("integral(negative(U*I))",data,interpolation="linear",unit="J")
    assert discharge.value == pytest.approx(3000-1450-100/3,abs=1e-9)
    assert discharge.value-regen.value == pytest.approx(result.value,abs=1e-9)


def test_sign_crossing_not_at_grid_midpoint_integrates_correctly():
    # Current crosses zero at t=.37, which is not a native sample or midpoint.
    data={"I":([0,1],[-.37,.63],"A")}
    positive=calculate("integral(positive(I))",data,end=1,interpolation="linear")
    negative=calculate("integral(negative(I))",data,end=1,interpolation="linear")
    assert positive.value == pytest.approx(.63**2/2,abs=1e-12)
    assert negative.value == pytest.approx(.37**2/2,abs=1e-12)


def test_narrow_clipped_polynomial_region_is_not_missed():
    data={"X":([0,1],[0,1],"")}
    # A very narrow peak entirely between quadrature nodes.
    result=calculate("integral(positive((X-.21)*(.22-X)))",data,end=1,interpolation="linear")
    assert result.status == "ok",result.message
    assert result.value == pytest.approx(.01**3/6,abs=1e-14)


def test_boundaries_and_asynchronous_alignment():
    data={"U":([0,1,2],[300,310,320],"V"),"I":([0,.5,1.5,2],[1,2,3,4],"A")}
    hold=calculate("integral(U*I)",data,start=.25,end=1.75)
    expected=.25*300*1+.5*300*2+.5*310*2+.25*310*3
    assert hold.value == pytest.approx(expected)
    linear=calculate("integral(X)",{"X":([0,2],[0,2],"")},start=.25,end=1.75,interpolation="linear")
    assert linear.value == pytest.approx((1.75**2-.25**2)/2)


def test_hold_age_gaps_have_exact_coverage_and_no_partial_total():
    result=calculate("integral(X)",{"X":([0,10],[2,2],"")},end=10,max_gap=2)
    assert result.status == "incomplete"
    assert result.value is None
    assert result.coverage == pytest.approx(.2)


def test_linear_gap_exact_native_values_still_available():
    t=np.array([0.,10.]);v=np.array([2.,3.])
    assert np.allclose(align_values(t,v,[0,10],"linear",2),[2,3])
    assert np.isnan(align_values(t,v,[1],"linear",2)[0])
    result=calculate("integral(X)",{"X":(t,v,"")},end=10,max_gap=2,interpolation="linear")
    assert result.status == "incomplete" and result.coverage == 0


def test_nan_interval_invalidates_total_and_preserves_coverage():
    result=calculate("integral(X)",{"X":([0,1,2],[1,np.nan,2],"")})
    assert result.status == "incomplete" and result.value is None
    assert result.coverage == pytest.approx(.5)


def test_outside_signal_bounds_not_extrapolated():
    result=calculate("integral(X)",{"X":([.5,1.5],[1,1],"")},max_gap=10)
    assert result.status == "incomplete" and result.value is None
    assert result.coverage == pytest.approx(.5)


@pytest.mark.parametrize("expression",["integral(1 / (X-.37))","integral(1 / ((X-.37)**2))", "integral(X) / 0"])
def test_denominator_zero_between_samples_or_in_scalar_is_invalid(expression):
    result=calculate(expression,{"X":([0,1],[0,1],"")},end=1,interpolation="linear")
    assert result.status == "invalid" and result.value is None


def test_unit_dimensions_check_and_unknown_unit_message():
    data={"U":([0,2],[400,400],"V"),"I":([0,2],[10,10],"A")}
    good=calculate("integral(U*I)/3600000",data,unit="kWh")
    assert good.status == "ok" and good.value == pytest.approx(8000/3600000)
    assert calculate("mean(U+I)",data).status == "invalid"
    assert calculate("integral(U*I)",data,unit="A").status == "invalid"
    unknown=calculate("mean(X)",{"X":([0,2],[1,1],"custom")})
    assert unknown.status == "ok" and "Chưa xác minh" in unknown.message


def test_formula_application_is_explicit_and_results_are_separate():
    store=MemoryStore({"X":([0,1,2],[1,2,3],"")})
    a,b=Segment("A",0,1),Segment("B",1,2)
    formula=Formula("Energy","integral(X)",{"X":"X"})
    assert evaluate_all(store,[formula],[a,b]) == []
    assert evaluate_formula(store,formula,a).status == "not_applied"
    formula.segment_ids=[b.id]
    results=evaluate_all(store,[formula],[a,b])
    assert len(results)==1 and results[0].segment_id==b.id and results[0].value == 2
    formula.segment_ids=[a.id,b.id]
    assert [r.value for r in evaluate_all(store,[formula],[a,b])] == [1,2]


def test_cancellation_propagates_instead_of_becoming_result():
    store=MemoryStore({"X":([0,1],[1,2],"")})
    segment=Segment("A",0,1)
    formula=Formula("x","integral(X)",{"X":"X"},segment_ids=[segment.id])
    token=CancellationToken(); token.cancel()
    with pytest.raises(CancelledError):
        evaluate_formula(store,formula,segment,token)


def test_trace_has_nan_breaks_for_missing_data_and_rejects_aggregates():
    store=MemoryStore({"X":([0,10],[1,2],"")})
    segment=Segment("A",0,10)
    formula=Formula("x","X*2",{"X":"X"},segment_ids=[segment.id],max_gap=2)
    t,v=evaluate_trace(store,formula,segment)
    assert np.all(np.diff(t)>0) and t[0]==0 and t[-1]==10
    assert v[0]==2 and v[-1]==4 and np.isnan(v).any()
    formula.expression="integral(X)"
    with pytest.raises(ValueError):
        evaluate_trace(store,formula,segment)


def test_chunked_grid_never_changes_sample_count_or_integral(monkeypatch):
    # Explicit patch wrapper exercises more than one merge chunk without huge data.
    from vehiclelog.calculations import timeline
    original=timeline.iter_time_grid
    monkeypatch.setattr(timeline,"iter_time_grid",lambda arrays,segment,interpolation,max_gap:original(arrays,segment,interpolation,max_gap,chunk_size=3))
    t=np.arange(0,20,dtype=float)
    data={"X":(t,t,"")}
    result=calculate("integral(X)",data,end=19,max_gap=.7)
    assert result.status=="incomplete" and result.coverage==pytest.approx(.7)
    assert calculate("sample_mean(X)",data,end=19,max_gap=2).value==pytest.approx(9.5)
    assert calculate("integral(X)",data,end=19,max_gap=2).value==pytest.approx(sum(range(19)))


def test_extremum_of_linear_product_found_inside_interval():
    data={"X":([0,1],[0,1],"")}
    result=calculate("max(X*(1-X))",data,end=1,interpolation="linear")
    assert result.status == "ok" and result.value==pytest.approx(.25)


def test_constant_formula_and_bad_max_gap():
    assert calculate("2+3",{},end=1).value==5
    for gap in (0,-1,np.nan,np.inf):
        result=calculate("integral(X)",{"X":([0,1],[1,1],"")},end=1,max_gap=gap)
        assert result.status=="invalid"


def test_formula_kind_and_trace_calculation_status():
    from vehiclelog.formulas import formula_kind
    store=MemoryStore({"X":([0,1],[1,2],"")})
    segment=Segment("A",0,1)
    formula=Formula("x","X*2",{"X":"X"},segment_ids=[segment.id])
    assert formula_kind(formula)=="trace"
    assert evaluate_formula(store,formula,segment).status=="trace"
    formula.expression="integral(X)"
    assert formula_kind(formula)=="scalar"
    formula.expression="integral(X)+X"
    with pytest.raises(ValueError):
        formula_kind(formula)
    assert evaluate_formula(store,formula,segment).status=="invalid"


def test_safe_div_refuses_small_or_negative_threshold_denominator():
    for expression in ("safe_div(2,0,.001)","safe_div(2,.0005,.001)","safe_div(2,1,-1)"):
        assert calculate(expression,{},end=1).status=="invalid"
    assert calculate("safe_div(2,.1,.001)",{},end=1).value==pytest.approx(20.)
    result=calculate("integral(safe_div(1,X,.01))",{"X":([0,1],[-1,1],"")},end=1,interpolation="linear")
    assert result.status=="invalid" and result.value is None


def test_nonpolynomial_denominator_with_two_narrow_zeros_rejected():
    result=calculate("integral(1/(abs(X-.2)-.001))",{"X":([0,1],[0,1],"")},end=1,interpolation="linear")
    assert result.status=="invalid" and result.value is None


def test_linear_sqrt_quadrature_and_abs_minimum_at_crossing():
    data={"X":([0,1],[0,1],"")}
    assert calculate("integral(sqrt(X))",data,end=1,interpolation="linear").value==pytest.approx(2/3,abs=1e-10)
    assert calculate("min(abs(X-.37))",data,end=1,interpolation="linear").value==pytest.approx(0,abs=1e-12)
    assert calculate("integral(sqrt(-X))",data,end=1,interpolation="linear").status=="invalid"


def test_stream_trace_matches_materialized_trace_and_bounded_chunks(monkeypatch):
    import vehiclelog.formulas as module
    from vehiclelog.calculations import timeline
    original=timeline.iter_time_grid
    monkeypatch.setattr(timeline,"iter_time_grid",lambda arrays,segment,interpolation,max_gap:original(arrays,segment,interpolation,max_gap,chunk_size=5))
    store=MemoryStore({"X":(np.arange(100),np.arange(100),"")})
    segment=Segment("A",0,99)
    formula=Formula("x","X*2",{"X":"X"},segment_ids=[segment.id],max_gap=2)
    chunks=list(module.iter_evaluate_trace(store,formula,segment))
    assert len(chunks)>1 and all(len(t)<=6 for t,v in chunks)
    t=np.concatenate([t for t,v in chunks]);v=np.concatenate([v for t,v in chunks])
    actual_t,actual_v=evaluate_trace(store,formula,segment)
    np.testing.assert_equal(t,actual_t);np.testing.assert_equal(v,actual_v)
    assert np.all(np.diff(t)>0)


def test_nonlinear_inner_extremum_is_bounded_not_just_sampled():
    data={"X":([0,1],[0,1],"")}
    result=calculate("max(X*sqrt(1-X))",data,end=1,interpolation="linear")
    assert result.status=="ok",result.message
    assert result.value==pytest.approx(2/(3*np.sqrt(3)),abs=1e-9)


def test_regular_decimal_timestamp_spacing_does_not_create_false_gaps():
    t=np.arange(1001)*.1
    result=calculate("integral(X)",{"X":(t,np.ones_like(t),"")},end=100,max_gap=.1,interpolation="linear")
    assert result.status=="ok" and result.value==pytest.approx(100.)


def test_union_merge_bounds_total_chunk_size_with_many_signals():
    from vehiclelog.calculations.timeline import iter_time_grid
    segment=Segment("A",0,100)
    arrays={str(i):(np.arange(0,100,.1)+i*.001,np.ones(1000)) for i in range(20)}
    grids=list(iter_time_grid(arrays,segment,"hold",.3,chunk_size=128))
    assert len(grids)>1
    assert max(len(grid) for grid in grids)<=129
    assert grids[0][0]==0 and grids[-1][-1]==100
    assert all(np.all(np.diff(grid)>0) for grid in grids)


def test_sqrt_polynomial_domain_handles_correlated_terms_and_exact_square():
    data={"X":([0,1],[0,1],"")}
    semicircle=calculate("integral(sqrt(X-X**2))",data,end=1,interpolation="linear")
    assert semicircle.status=="ok",semicircle.message
    assert semicircle.value==pytest.approx(np.pi/8,abs=1e-10)
    square=calculate("integral(sqrt((X-.37)**2))",data,end=1,interpolation="linear")
    assert square.status=="ok",square.message
    assert square.value==pytest.approx((.37**2+.63**2)/2,abs=1e-10)

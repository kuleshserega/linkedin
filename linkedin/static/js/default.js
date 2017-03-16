$(document).ready(function(){
    $('.form-group').click(function(){
        $(this).find('input').removeClass('required');
        $(this).find('.errorlist').remove();
    });

    $('#id_date_start, #id_date_end, input[name=work_from_date]').datepicker(
        { 
            dateFormat: 'yy-mm-dd',
            changeMonth: true,
            changeYear: true,
        }
    );

    $('#id_working_now').click(function(){
        $('.errorlist').remove();
        var now = formatDate();
        if ($(this).is(':checked')){
            $('#id_date_end').val(now).parent().hide();
        } else {
            $('#id_date_end').val('').parent().show();
        }
    });

    $('body').on('click', '.chosen-choices, form input, form textarea, form select', function(){
        $(this).closest('p').prev('.errorlist').remove();
    });

    function formatDate() {
        var d = new Date(),
            month = '' + (d.getMonth() + 1),
            day = '' + d.getDate(),
            year = d.getFullYear();

        if (month.length < 2) month = '0' + month;
        if (day.length < 2) day = '0' + day;

        return [year, month, day].join('-');
    }

    if ($('#id_url_does_not_exist').is(':checked')) {
        $('#id_url').val('http://').parent().hide();
    } else {
        $('#id_reason').parent().hide();
    }

    $('#id_url_does_not_exist').click(function(){
        $('.errorlist').remove();
        if ($(this).is(':checked')){
            $('#id_reason').parent().show();
            $('#id_url').val('').parent().hide();
        } else {
            $('#id_reason').parent().hide();
            $('#id_url').val('http://').parent().show();
        }
    });

    if ($('#user_id').val() != ''){
        $('#id_developer').parent().replaceWith('<input type="hidden" id="id_developer" value="' + $('#user_id').val() + '" name="developer">')        
    }

    $('#id_search').bind('keyup change', function(ev) {
        var searchTerm = $(this).val();
        $('body').removeHighlight();
        if (searchTerm) {
            $('body').highlight(searchTerm);
        }
    });
});

$(document).ready(function(){
  $('#searchbtn').on('click', function(e){
    e.preventDefault();
    var search_term = $('#id_search').val();
    var search_type = $('#search_type').val();
    $.ajax({
      url: '/run-search/?search=' + search_term + '&search_type=' + search_type,
      method: 'GET',
      success: function(data){
        show_msg(data);
        $('#id_search').val('');
        $('.messages').find('.alert').each(function(){
          var el = $(this);
          setTimeout(function(){
            el.fadeOut(500, function(){
             el.remove();
            });
          }, 4000);
        });
      }
    });
  });

  var queryDict = {}
  location.search.substr(1).split("&").forEach(
    function(item){
      queryDict[item.split("=")[0]] = item.split("=")[1]
    }
  );
  if (queryDict["page"] != undefined){
    var page = queryDict['page'];
  } else {
    var page = 1;
  }

  setInterval(function(){
    $.ajax({
      url: '/get_companies_list/?page=' + page,
      method: 'GET',
      success: function(data){
        var html = [];
        html.push(thead_html);
        for (var i=0;i<data['content'].length;i++){
          html.push(get_row_html(data['content'][i]));
        }

        $('#allProjectsTable').html(html.join());
      }
    });
  }, 5000);

  var thead_html = '<thead>' +
    '<tr>' +
      '<th>ID</th>' +
      '<th>Search company</th>' +
      '<th>Company ID</th>' +
      '<th>Supervisors by GEO</th>' +
      '<th>Date</th>' +
      '<th>Status</th>' +
      '<th>Link to search details</th>' +
      '<th>Save to CSV</th>' +
    '</tr>' +
  '</thead>';

  var get_row_html = function(row){
    var search_company = '';
    if(row['search_company']){ search_company = row['search_company']; }

    var companyId = '';
    if(row['companyId']){ companyId = row['companyId']; }

    var geo = '';
    if(row['geo']){ geo = row['geo']; }

    var row_template_html = '<tr>' +
      '<td>' + row['id'] + '</td>' +
      '<td>' + search_company + '</td>' +
      '<td>' + companyId + '</td>' +
      '<td>' + geo + '</td>' +
      '<td>' + row['date_created'] + '</td>' +
      '<td><span title="' + row['status_text'] + '" class="center glyphicon ' + row['status_icon'] + '"></span></td>' +
      '<td><a title="Search details" target="_blank" class="center" href="' + row['search_details_url'] + '"><img width=25 src="/static/img/details.png" /></a></td>' +
      '<td><a title="Save to CSV" class="center" href="' + row['employees_to_csv'] + '"><img width=25 src="/static/img/save.png" /></a></td>' +
    '</tr>';

    return row_template_html;
  }

  var show_msg = function(data){
    msg_block = '<div class="alert alert-' + data['status'] + '">' +
      '<span>' + data['msg'] + '</span>' +
    '</div>';

    $('.messages').html(msg_block);
  }

  $('#search_type').on('change', function(){
    if ($(this).val() == '1'){
      $('#id_search').attr('placeholder', 'Company name or ID');
    } else if ($(this).val() == '2'){
      $('#id_search').attr('placeholder', 'Location');
    }
  });
});
